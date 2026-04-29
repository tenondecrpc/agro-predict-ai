## Why

The ARQ queue transport exists for enqueueing jobs but there is no worker process to consume and execute them. The webhook endpoint accepts events and enqueues them, but without a running ARQ worker those jobs sit in Redis forever. This blocks the asynchronous prediction pipeline (data ingestion -> webhook -> ARQ worker -> LangGraph graph -> recommendation).

## What Changes

- Add ARQ worker process entry point with `WorkerSettings` class
- Wire worker to consume prediction pipeline jobs from Redis queues
- Add worker health check with active job reporting
- Add Docker Compose service for local worker development
- Add Kubernetes Deployment + HPA for worker in Helm charts
- Add graceful shutdown with checkpoint boundary completion

## Capabilities

### New Capabilities
- `arq-worker-process`: ARQ worker entry point, job handlers, graceful shutdown, health reporting
- `arq-worker-deployment`: Docker Compose service, Kubernetes deployment, HPA, resource quotas

### Modified Capabilities
- `queue-resilience`: ARQ worker is now a deployable component (previously only queue transport existed)

## Impact

- `backend/src/backend/worker.py` - new `WorkerSettings` class and job handler registration
- `backend/src/backend/persistence/worker.py` - wire job handlers to existing `RedisWorkerController`
- `docker-compose.yml` - new worker service
- `helm/templates/` - worker deployment, HPA, service account
- `k8s/` - optional local worker manifest
- `Makefile` - new targets for worker development
