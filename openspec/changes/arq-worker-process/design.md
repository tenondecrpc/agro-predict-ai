## Context

The ARQ queue transport (`persistence/worker.py`) already supports enqueueing jobs via `ArqQueueTransport.enqueue()`. The `WorkerBootstrap` class in `worker.py` provides a `WorkerController` for job coordination, drain leases, and DLQ management. However, there is no ARQ `WorkerSettings` class or worker process entry point to actually consume and execute jobs from Redis queues.

The prediction pipeline (`predictions/graph.py`) has a fully implemented `PredictionGraph` with five agents: `data_analyst -> ml_executor -> recommendation_engine -> explainability -> reviewer`. The `/api/v1/runtime/simulate` endpoint runs this graph synchronously. The webhook endpoint enqueues jobs but nothing processes them.

The existing `worker.py` has `process_metering_rollups`, `process_encryption_key_rotation`, and `process_knowledge_ingestion` functions, but none of them are registered as ARQ job handlers.

## Goals / Non-Goals

**Goals:**
- Create an ARQ `WorkerSettings` class that registers job handlers for the prediction pipeline
- Wire the worker to execute `PredictionGraph` asynchronously from queued jobs
- Support graceful shutdown via SIGTERM/SIGINT with checkpoint boundary completion
- Add Docker Compose service for local worker development
- Add Kubernetes Deployment + HPA for worker in Helm charts
- Report worker health (active jobs, queue depth, error rate)

**Non-Goals:**
- Do not change the prediction graph logic itself
- Do not add new queue types beyond the existing `ticket-runs` queue
- Do not implement a separate worker UI (DLQ viewing is via API)
- Do not change the webhook endpoint behavior

## Decisions

### 1. WorkerSettings as a module-level constant in worker.py

**Decision:** Define `WorkerSettings` in `backend/src/backend/worker.py` as a module-level constant that ARQ can import directly (e.g., `arq backend.worker.WorkerSettings`).

**Rationale:** ARQ expects a `WorkerSettings` class with `functions` and optionally `on_startup`, `on_shutdown`, `max_jobs`, etc. This is the standard ARQ pattern. Keeping it in the existing `worker.py` avoids creating a new module and keeps all worker-related code together.

**Alternatives considered:**
- Separate `worker_settings.py` module — adds indirection without benefit
- Dynamic settings generation — unnecessary complexity; static config is sufficient

### 2. Job handler: `process_prediction_run`

**Decision:** Create a single ARQ job handler `process_prediction_run` that receives the job kwargs (tenant_id, team_id, run_id, etc.), builds a `PredictionInput`, executes the `PredictionGraph`, and stores the result via the persistence layer.

**Rationale:** The prediction pipeline is a single logical unit. One handler keeps the flow simple. The handler will:
1. Build `PredictionGraph` with configured agents
2. Build `PredictionInput` from job kwargs
3. Execute the graph
4. Store the `PredictionOutput` via `PostgresRunRepository`
5. Update worker controller state (checkpoint, in-flight counter)

**Alternatives considered:**
- Separate handlers per agent — adds complexity, breaks atomicity of a single prediction run
- Reuse simulate endpoint logic — the simulate endpoint is synchronous HTTP; the worker needs async ARQ context

### 3. Graceful shutdown via ARQ's built-in signal handling

**Decision:** Use ARQ's built-in `on_shutdown` hook combined with the existing `RedisWorkerController.begin_drain()` and `checkpoint_and_release()` methods. On SIGTERM, the worker will:
1. Call `begin_drain(worker_id)` to stop accepting new jobs
2. Let the current job complete (ARQ's default behavior)
3. Call `checkpoint_and_release(worker_id, checkpoint_ref)` on completion
4. Exit cleanly

**Rationale:** ARQ already handles SIGTERM/SIGINT gracefully by finishing the current job. We augment this with our worker controller's drain/checkout protocol.

### 4. Docker Compose worker service

**Decision:** Add a `worker` service to `docker-compose.yml` that uses the same image/environment as the backend but runs `uv run --project backend arq backend.worker.WorkerSettings`.

**Rationale:** The worker shares the same codebase and dependencies as the backend. A separate service with the same build context is the simplest approach.

### 5. Kubernetes worker deployment

**Decision:** The Helm chart already has `worker-rollout.yaml` and `hpa-worker.yaml` templates. Update them to reference the correct container command (`arq backend.worker.WorkerSettings`) and ensure environment variables are wired correctly.

**Rationale:** The templates exist but may not be fully wired. We verify and update rather than create from scratch.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| Worker crashes during graph execution, job lost | ARQ retries automatically; after max retries, DLQ captures the failure via `capture_terminal_failure()` |
| Multiple workers process the same job | ARQ guarantees exactly-once delivery per job ID; job ID is set by the enqueueing side |
| Worker starts before Redis is ready | ARQ connection retry logic; add `depends_on` with health check in Docker Compose |
| Prediction graph takes longer than ARQ job timeout | Default ARQ timeout is 300s; configurable per job; long-running predictions should set `_job_timeout` |
| Memory growth from loading ML models | Each worker process loads models once; HPA scales based on queue depth, not CPU |
