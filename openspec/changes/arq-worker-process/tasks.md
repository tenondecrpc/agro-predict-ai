## 1. WorkerSettings and job handler

- [ ] 1.1 Create `process_prediction_run` async function in `backend/src/backend/worker.py` that accepts ARQ context and job kwargs
- [ ] 1.2 Build `PredictionInput` from job kwargs (tenant_id, team_id, run_id, prediction data)
- [ ] 1.3 Instantiate `PredictionGraph` and execute it within `process_prediction_run`
- [ ] 1.4 Store `PredictionOutput` via `PostgresRunRepository` on success
- [ ] 1.5 Capture terminal failures via `RedisWorkerController.capture_terminal_failure()` on exception
- [ ] 1.6 Update worker controller state (in-flight counter, checkpoint release) after job completion
- [ ] 1.7 Create `WorkerSettings` class with `functions` tuple registering `process_prediction_run`
- [ ] 1.8 Add `on_startup` hook to build `WorkerBootstrap` and register worker ID
- [ ] 1.9 Add `on_shutdown` hook to call `begin_drain(worker_id)`
- [ ] 1.10 Add configurable job timeout via `BACKEND_WORKER_JOB_TIMEOUT_SECONDS` env var

## 2. Worker health reporting

- [ ] 2.1 Add worker status fields to health check response (active job count, queue depth)
- [ ] 2.2 Implement queue depth threshold check for degraded status

## 3. Tests

- [ ] 3.1 Write unit tests for `process_prediction_run` happy path (mock graph, mock repository)
- [ ] 3.2 Write unit tests for `process_prediction_run` failure path (graph exception, DLQ capture)
- [ ] 3.3 Write unit tests for `WorkerSettings` lifecycle hooks
- [ ] 3.4 Write integration test: enqueue job via ARQ, worker processes it, result stored in PostgreSQL

## 4. Docker Compose

- [ ] 4.1 Add `worker` service to `docker-compose.yml` with same build context as backend
- [ ] 4.2 Configure worker command: `uv run --project backend arq backend.worker.WorkerSettings`
- [ ] 4.3 Add `depends_on` with Redis health check
- [ ] 4.4 Update `make local-up` to start worker service
- [ ] 4.5 Update `make local-down` to stop worker service

## 5. Kubernetes / Helm

- [ ] 5.1 Verify `helm/templates/worker-rollout.yaml` uses correct container command
- [ ] 5.2 Verify `helm/templates/hpa-worker.yaml` scales on ARQ queue length metric
- [ ] 5.3 Add resource requests/limits to worker deployment (512Mi/1Gi memory, 250m/500m CPU)
- [ ] 5.4 Ensure worker deployment receives same env vars as backend (database, Redis, encryption)

## 6. Documentation

- [ ] 6.1 Update README.md with worker development instructions
- [ ] 6.2 Update README.md roadmap table for spec 012-queue-resilience status
- [ ] 6.3 Add Makefile target `make dev-worker` for local worker development
