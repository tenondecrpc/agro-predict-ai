# Feature Specification: Async ARQ Dispatch for Predictions

**Feature Branch**: `014-async-arq-dispatch`
**Created**: 2026-04-28
**Status**: Draft
**Input**: Wire the ARQ queue into the prediction HTTP path so that long-running predictions are dispatched as background jobs and callers receive a job ID for async polling instead of blocking on the full pipeline.

## Context

`POST /api/v1/predictions` currently calls `PredictionService.execute()` synchronously and blocks the HTTP connection until the full LangGraph graph completes. The ARQ worker handler `process_prediction_run` in `backend/src/backend/worker.py` is fully implemented but is never enqueued from the HTTP path. `ArqQueueTransport.enqueue()` in `backend/src/backend/persistence/worker.py` wraps `arq.create_pool().enqueue_job()` but is not called anywhere in the request lifecycle. This spec covers wiring the async path: the HTTP endpoint enqueues the job, returns 202 Accepted with a `run_id`, and the caller polls a status endpoint.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Submit prediction and receive immediate job ID (Priority: P1)

A client submits a prediction request to `POST /api/v1/predictions`. The endpoint validates the request, enqueues a job via `ArqQueueTransport`, and returns `202 Accepted` with a `run_id` and a `status_url`. The client does not wait for the full pipeline to complete. The LangGraph graph runs in the ARQ worker process.

**Why this priority**: This is the core gap. Without async dispatch, the HTTP server blocks for the full graph execution duration (potentially 30-45 seconds with LLM), causing timeouts under load.

**Independent Test**: Submit a prediction request and assert the HTTP response code is `202` and the body contains a non-empty `run_id`. Verify a job appears in the ARQ queue using `ArqQueueTransport.queued_jobs()`. No pipeline result should be present yet.

**Acceptance Scenarios**:

1. **Given** a valid prediction request, **When** `POST /api/v1/predictions` is called, **Then** the response is `202 Accepted` with `{"run_id": "<uuid>", "status": "queued", "status_url": "/api/v1/predictions/<run_id>"}`.
2. **Given** Redis is unavailable, **When** a prediction request is submitted, **Then** the endpoint returns `503 Service Unavailable` with a structured error body and no partial job is created.
3. **Given** tenant concurrency limit is reached, **When** a new prediction is submitted for that tenant, **Then** the endpoint returns `429 Too Many Requests` with a `Retry-After` header.

---

### User Story 2 - Poll prediction status until completion (Priority: P1)

The client polls `GET /api/v1/predictions/{run_id}` with its `tenant_id`. While the job is running, the endpoint returns `{"status": "running", "progress": {"current_node": "ml_executor"}}`. When the job completes, it returns the full prediction output. If the job fails, it returns the escalation reason.

**Why this priority**: Without a polling endpoint, the async submission is useless - callers have no way to retrieve results.

**Independent Test**: Submit a prediction, extract `run_id`, poll every second until `status == "completed"`, and verify the response matches the full `PredictionOutput` schema.

**Acceptance Scenarios**:

1. **Given** a queued job, **When** `GET /api/v1/predictions/{run_id}` is polled before completion, **Then** the response includes `status: "running"` and the name of the currently executing graph node.
2. **Given** a completed job, **When** `GET /api/v1/predictions/{run_id}` is called, **Then** the response includes the full prediction output, confidence interval, feature importance, and explanation artifact.
3. **Given** a run_id that does not belong to the requesting tenant, **When** `GET /api/v1/predictions/{run_id}` is called, **Then** the endpoint returns `404 Not Found` (tenant isolation - no information leakage).
4. **Given** a failed job, **When** `GET /api/v1/predictions/{run_id}` is called, **Then** the response includes `status: "failed"`, `escalation_reason`, and a reference to the dead letter record.

---

### User Story 3 - Dead letter queue handling for failed jobs (Priority: P2)

When a prediction job fails after all retries, it is written to the DLQ (`dead_letter_records` table). An operator can query failed jobs via `GET /api/v1/predictions?tenant_id=X&status=failed` and manually retry or dismiss them.

**Why this priority**: Production systems lose data silently if the DLQ is not monitored. Operators need visibility into failed predictions.

**Independent Test**: Inject a job that always fails (mock the graph to throw). Verify the job appears in `dead_letter_records` after max retries. Call the list endpoint with `status=failed` and confirm the job is returned.

**Acceptance Scenarios**:

1. **Given** a job fails on all retry attempts, **When** the ARQ worker exhausts retries, **Then** a `DeadLetterRecord` is written to PostgreSQL with the failure reason and job payload.
2. **Given** a dead letter record exists, **When** an operator calls `POST /api/v1/predictions/{run_id}/retry`, **Then** the job is re-enqueued and the DLQ record is archived.
3. **Given** an operator queries `GET /api/v1/predictions?status=failed`, **Then** only failed jobs belonging to the requesting tenant are returned.

---

### User Story 4 - Weighted fair queueing across tenants (Priority: P3)

Multiple tenants submit predictions simultaneously. The ARQ worker uses `WeightedFairDispatcher` to process jobs fairly without one tenant monopolizing the worker pool. Each tenant has a configurable weight and concurrency limit stored in the PostgreSQL config table.

**Why this priority**: Without fair dispatch, a high-volume tenant can starve others. The `WeightedFairDispatcher` already exists in `backend/src/backend/platform/queue.py` but is not connected to the ARQ worker selection logic.

**Independent Test**: Submit 10 jobs from tenant-A and 10 from tenant-B simultaneously. Verify the worker alternates between tenants rather than draining one queue entirely before starting the other.

**Acceptance Scenarios**:

1. **Given** tenant-A has weight 2 and tenant-B has weight 1, **When** both have queued jobs, **Then** tenant-A receives approximately twice as many worker slots as tenant-B.
2. **Given** tenant-A reaches its concurrency limit, **When** new jobs from tenant-A arrive, **Then** they are queued without being dispatched until a slot opens.

---

### Edge Cases

- What happens when the ARQ worker crashes between job dequeue and first checkpoint?
- How does graceful shutdown interact with an in-progress graph execution?
- What happens when a job's LangGraph checkpoint is orphaned (job removed from Redis but checkpoint remains in PostgreSQL)?
- How does the polling endpoint handle a `run_id` that is queued in Redis but not yet persisted to PostgreSQL?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `POST /api/v1/predictions` MUST enqueue a job via `ArqQueueTransport` and return `202 Accepted` with `run_id`, `status`, and `status_url`.
- **FR-002**: `GET /api/v1/predictions/{run_id}` MUST return job status, current graph node (when running), and full output (when completed).
- **FR-003**: The endpoint MUST enforce tenant isolation: `run_id` lookups MUST be scoped to the requesting tenant.
- **FR-004**: `POST /api/v1/predictions/{run_id}/retry` MUST re-enqueue a dead-lettered job and archive the original DLQ record.
- **FR-005**: The ARQ worker MUST write progress updates (current graph node) to Redis so the polling endpoint can serve live status without querying PostgreSQL on every poll.
- **FR-006**: Graceful shutdown MUST allow in-progress graph executions to complete up to a configurable drain timeout before the worker exits.
- **FR-007**: The worker MUST respect per-tenant concurrency limits read from the PostgreSQL config table via `WeightedFairDispatcher`.
- **FR-008**: Failed jobs MUST be written to `dead_letter_records` after max retries with full job payload and failure reason.
- **FR-009**: The endpoint MUST return `503` if Redis is unavailable at enqueue time.
- **FR-010**: The endpoint MUST return `429` with `Retry-After` header when the tenant concurrency limit is reached.
- **FR-011**: Job progress updates in Redis MUST have a TTL of at least 24 hours to support delayed polling.
- **FR-012**: The synchronous path (`PredictionService.execute()`) MAY be retained as an internal method for testing but MUST NOT be reachable from any public HTTP endpoint.

### Key Entities

- **PredictionJob**: ARQ job envelope. Fields: `run_id`, `tenant_id`, `team_id`, `prediction_input`, `model_version`, `enqueued_at`, `retry_count`.
- **JobStatus**: Redis hash per `run_id`. Fields: `status` (queued/running/completed/failed), `current_node`, `started_at`, `completed_at`, `error`.
- **DeadLetterRecord**: PostgreSQL record. Fields: `id`, `run_id`, `tenant_id`, `payload`, `failure_reason`, `failed_at`, `retry_count`, `archived`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `POST /api/v1/predictions` responds in under 200 ms at P95 (enqueue only, no graph execution in the HTTP thread).
- **SC-002**: 100% of submitted jobs either complete successfully or appear in `dead_letter_records` - zero silent failures.
- **SC-003**: Graceful shutdown completes within the configured drain timeout with no orphaned in-progress jobs.
- **SC-004**: Tenant isolation test: zero cross-tenant `run_id` leaks across 1000 random polling requests.
- **SC-005**: Weighted fair dispatch delivers within 20% of configured weight ratios under sustained mixed load.
