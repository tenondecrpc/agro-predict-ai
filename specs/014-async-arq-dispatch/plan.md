# Implementation Plan: Async ARQ Dispatch for Predictions

**Branch**: `014-async-arq-dispatch` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)

## Summary

Wire the existing ARQ infrastructure into the prediction HTTP path so that `POST /api/v1/predictions` enqueues jobs via `ArqQueueTransport`, returns 202 Accepted with a `run_id`, and callers poll `GET /api/v1/predictions/{run_id}/status` for results. Fix the retry endpoint, connect WeightedFairDispatcher, enforce tenant concurrency, and remove the synchronous fallback from public endpoints.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, ARQ, Redis 7, PostgreSQL 16, LangGraph
**Storage**: PostgreSQL (dead_letter_records, predictions), Redis (job status, queue)
**Testing**: pytest
**Target Platform**: Linux server (Kubernetes)
**Project Type**: Web service (backend API + workers)
**Performance Goals**: POST responds < 200ms P95 (enqueue only)
**Constraints**: Tenant isolation, graceful shutdown, DLQ with full payload
**Scale/Scope**: Multi-tenant, per-tenant concurrency limits

## Constitution Check

- **Agent-First Orchestration**: ARQ worker executes the LangGraph graph - no change to agent contracts. PASS.
- **Data-Driven Decisions**: Async path preserves data provenance chain. PASS.
- **Test-First Validation**: Tests for async enqueue, status polling, DLQ retry, tenant isolation. PASS.
- **Observability & Explainability**: Job progress in Redis, DLQ records in PostgreSQL. PASS.
- **Resilience & Graceful Degradation**: 503 on Redis down, drain timeout on shutdown, DLQ for failures. PASS.
- **Self-hosted only**: No vendor-hosted components. PASS.
- **Tenant isolation**: All endpoints scoped to tenant_id. PASS.

## Project Structure

### Documentation (this feature)

```text
specs/014-async-arq-dispatch/
├── spec.md              # Feature specification
├── plan.md              # This file
└── tasks.md             # Task list
```

### Source Code (repository root)

```text
backend/src/backend/predictions/
├── api.py               # Modified: wire redis_client, remove sync fallback, fix retry
├── job_status.py        # Existing: JobStatus dataclass
├── service.py           # Modified: remove sync execute from public path
backend/src/backend/
├── app.py               # Modified: pass redis_client to predictions router
├── worker.py            # Modified: drain timeout, full payload to DLQ, TTL refresh
├── persistence/
│   └── worker.py        # Modified: connect WeightedFairDispatcher to ARQ
├── platform/
│   └── queue.py         # Existing: WeightedFairDispatcher
backend/tests/
├── integration/
│   └── test_predictions_api.py  # Modified: async path tests
└── unit/
    └── test_arq_dispatch.py     # New: async dispatch unit tests
```

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Keep sync execute() as internal method | Testing and internal use | FR-012 allows retention as internal method, just not public |
