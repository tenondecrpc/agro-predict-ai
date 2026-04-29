# AgroPredict AI — Multi-Agent Predictive Intelligence Platform

A self-hosted, enterprise-grade multi-agent predictive intelligence system for agriculture and logistics. It uses LangGraph to orchestrate specialized agents that analyze data, execute ML models, and generate actionable recommendations - all running inside customer-owned Kubernetes infrastructure.

## How it works

A data ingestion event triggers the prediction pipeline. A LangGraph graph orchestrates five agents in sequence:

```
data_analyst -> ml_executor -> recommendation_engine -> explainability -> reviewer
```

Each step is guarded: no prediction reaches production unless data quality gates pass, the model executes successfully, explainability verification completes, and the reviewer approves. Any failure routes to a registered escalation sink instead of silently continuing.

## Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph StateGraph |
| API and webhooks | FastAPI |
| Queue and pub/sub | ARQ + Redis |
| Persistence | PostgreSQL 16 (predictions, config, audit, model metadata) |
| ML | scikit-learn (extensible adapter for deep learning) |
| Frontend | Vite + React + TypeScript |
| Integration | Oracle APEX adapter (read-only ingestion, audited write-back) |
| Secrets | HashiCorp Vault + External Secrets Operator |
| Observability | OpenTelemetry, Prometheus, Grafana, Loki |
| Delivery | Helm, Kubernetes (connected and air-gapped profiles) |

## Repository layout

```
backend/        FastAPI app, LangGraph graph, ARQ workers, ML adapters
frontend/       Monitoring dashboards and admin UI
helm/           Helm charts for Kubernetes (connected and air-gapped)
k8s/            Base Kubernetes manifests for local development
contracts/      Machine-readable API contracts and model validation registries
operations/     Deployable operational artifacts such as alerts and dashboards
docs/           Human-readable operator, integrator, and developer documentation
specs/          SpecKit feature specifications (user stories, plans, tasks)
```

## Prerequisites

| Tool | Minimum version | Purpose |
|---|---|---|
| Python | 3.12+ | Backend runtime |
| uv | latest | Python dependency management |
| Node.js | 18+ | Frontend build and dev server |
| Docker | 20+ | Local dependencies and Minikube image builds |
| Docker Compose | 2.20+ | Local PostgreSQL and Redis |
| minikube | 1.30+ | Local Kubernetes cluster |
| kubectl | 1.28+ | Kubernetes CLI |
| make | 3.81+ | Build and development automation |

Install [uv](https://docs.astral.sh/uv/) if you do not have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Required environment variables

The backend requires these variables at startup. Without them the process exits immediately with a `RuntimeError`.

| Variable | Required | Source | Notes |
|---|---|---|---|
| `BACKEND_ENCRYPTION_ACTIVE_KEY_ID` | Yes | Secret | Key identifier (e.g. `kek-dev-v1`) |
| `BACKEND_ENCRYPTION_ACTIVE_WRAPPING_KEY` | Yes | Secret | Fernet symmetric key (32-byte URL-safe base64) |
| `BACKEND_WEBHOOK_SHARED_SECRET` | Yes | Secret | HMAC shared secret for webhook verification |
| `BACKEND_DEPLOYMENT_PROFILE` | No | ConfigMap | `connected` or `air_gapped` (default: `connected`) |
| `BACKEND_DATABASE_URL` | No | Secret | PostgreSQL URL. Without it, persistence shows "not configured" |
| `BACKEND_REDIS_URL` | No | Secret | Redis URL. Without it, queue shows "not configured" |

The `make minikube-secrets` target generates safe dev defaults for all required values. For local development without Kubernetes, `make dev-backend` auto-generates them if not already set in your environment.

## Local development

You have two options for running the system locally. Choose the one that fits your workflow.

| Option | Use case | PostgreSQL | Redis | Kubernetes |
|---|---|---|---|---|
| **A - Docker Compose + native processes** | Daily development, fast iteration | Yes (Docker) | Yes (Docker) | No |
| **B - Minikube** | Validate Kubernetes manifests, Helm charts, networking | No (placeholder) | No (placeholder) | Yes |

### Option A - Docker Compose + native processes (recommended)

This is the fastest way to get a fully functional local environment. PostgreSQL and Redis run in Docker containers while the backend and frontend run natively on your machine with hot reload.

#### Step 1 - Start dependencies

```bash
make local-up
```

This starts:
- **PostgreSQL 16** with `pgvector` on port `5432`
- **Redis 7** on port `6379`

Both services persist data in named Docker volumes and expose health checks.

#### Step 2 - Start the backend

```bash
make dev-backend
```

The Makefile automatically wires `BACKEND_DATABASE_URL` and `BACKEND_REDIS_URL` to the local Docker services unless you already have them set in your environment. The backend starts on http://127.0.0.1:8000 with hot reload.

To verify everything is connected, open another terminal:

```bash
curl -s http://127.0.0.1:8000/healthz | python3 -m json.tool
```

You should now see `database` and `redis` as `configured: true`.

#### Step 3 - Start the frontend

```bash
make dev-frontend
```

The dev server starts on http://127.0.0.1:5173. It proxies API requests to the local backend automatically.

#### Full pipeline test

With both backend and frontend running:

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"tenant-alpha","team_id":"team-core","crop":"corn","region":"midwest_us","time_horizon_days":30,"input_data":{"soil_moisture":0.35,"temperature_c":22.5,"rainfall_mm":45.0}}' | python3 -m json.tool
```

#### Stop dependencies

```bash
make local-down
```

This stops and removes the containers and volumes. To only stop without removing volumes, run `docker compose down`.

#### Full local flow - all services (OpenCode-Go base)

This section consolidates every step to run the complete pipeline locally with OpenCode-Go as the LLM provider. Each process runs in its own terminal.

**Terminal 1 - Infrastructure (PostgreSQL + Redis):**

```bash
make local-up
```

**Terminal 2 - Oracle XE (optional, for APEX integration testing):**

```bash
docker compose --profile oracle up -d
```

**Terminal 3 - Backend (with OpenCode-Go as LLM provider):**

```bash
export BACKEND_PROVIDER_OPENCODE_GO_ENDPOINT="http://localhost:8080/v1"
make dev-backend
```

> OpenCode-Go must be running on port 8080. If you use a different port or hostname, adjust the endpoint URL accordingly.

**Terminal 4 - Frontend:**

```bash
make dev-frontend
```

**Terminal 5 - ARQ Worker (optional, for async webhook processing):**

```bash
make dev-worker
```

**Verify the full stack:**

```bash
# Health check - database and redis should show configured: true
curl -s http://127.0.0.1:8000/healthz | python3 -m json.tool

# Full prediction pipeline (synchronous, no worker needed)
curl -s -X POST http://127.0.0.1:8000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"tenant-alpha","team_id":"team-core","crop":"corn","region":"midwest_us","time_horizon_days":30,"input_data":{"soil_moisture":0.35,"temperature_c":22.5,"rainfall_mm":45.0}}' | python3 -m json.tool
```

**Stop everything:**

```bash
make local-down
docker compose --profile oracle down   # if Oracle was started
```

#### Useful targets

```bash
make local-up      # Start PostgreSQL + Redis
make local-down    # Stop and remove containers/volumes
make local-logs    # Tail Docker Compose logs
make local-status  # Show running containers
make dev-backend   # Run backend with uv (hot reload)
make dev-frontend  # Run frontend with Vite (hot reload)
```

### Option B - Minikube

Use this option when you need to validate Kubernetes manifests, Helm charts, NetworkPolicies, or deployment configurations. Note that the local Minikube setup does **not** deploy PostgreSQL or Redis - the backend starts in a degraded mode where persistence and queues show "not configured".

#### Quick start

```bash
# Start Minikube
minikube start --driver=docker --memory=4g --cpus=2

# Build, configure, and deploy (one command)
make minikube-up
```

`make minikube-up` performs these steps in order:

1. **check-prereqs** - verifies all required tools are installed and Minikube is running
2. **minikube-images** - builds backend and frontend images inside Minikube
3. **minikube-secrets** - generates dev encryption keys and webhook secrets, applies them as a Kubernetes Secret
4. **minikube-deploy** - applies all manifests from `k8s/`
5. **minikube-wait** - waits for both pods to reach Ready status

#### Access the services

Minikube with the Docker driver does not expose NodePort services directly on the host IP. Use one of these methods:

**Option A - Port-forward (recommended):**

```bash
# Run in a terminal - this blocks until you press Ctrl+C
make port-forward

# Then open in your browser:
#   Backend API docs: http://127.0.0.1:18000/docs
#   Frontend UI:      http://127.0.0.1:18080
```

Or manually in separate terminals:

```bash
kubectl port-forward svc/backend 18000:8000    # terminal 1
kubectl port-forward svc/frontend 18080:80     # terminal 2
```

**Option B - Minikube service tunnel (opens browser automatically):**

```bash
minikube service backend   # opens API docs in browser
minikube service frontend  # opens UI in browser
```

| Service | URL |
|---|---|
| Backend API | http://127.0.0.1:18000 |
| API docs (Swagger) | http://127.0.0.1:18000/docs |
| Frontend UI | http://127.0.0.1:18080 |

> The port-forward must be running in a separate terminal for these localhost URLs to work.
> If your curl returns an empty response or "Connection refused", the port-forward is not active.

#### Testing the system on Minikube

There are two ways to exercise the backend: the **simulate endpoint** (synchronous, runs the full graph in one request) and the **webhook endpoint** (asynchronous, requires an ARQ worker). For local validation, use the simulate endpoint.

**Step 1 - Verify the backend is healthy**

With port-forward running in another terminal:

```bash
curl -s http://127.0.0.1:18000/healthz | python3 -m json.tool
```

Expected response:

```json
{
    "status": "ok",
    "reasons": [],
    "persistence": {
        "database": {"name": "database", "configured": false, "healthy": false},
        "redis": {"name": "redis", "configured": false, "healthy": false},
        "encryption": {"name": "encryption", "configured": true, "healthy": true}
    }
}
```

`"status": "ok"` and `"encryption": {"configured": true}` are the two things that matter. Database and Redis show `"configured": false` in local Minikube - this is expected.

**Step 2 - Run the full prediction pipeline**

```bash
curl -s -X POST http://127.0.0.1:18000/api/v1/predictions \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "tenant-alpha",
    "team_id": "team-core",
    "crop": "corn",
    "region": "midwest_us",
    "time_horizon_days": 30,
    "input_data": {
      "soil_moisture": 0.35,
      "temperature_c": 22.5,
      "rainfall_mm": 45.0
    }
  }' | python3 -m json.tool
```

This endpoint runs the entire LangGraph graph synchronously. It takes a few seconds. Look for these fields in the response:

| Field | Expected value | What it means |
|---|---|---|
| `status` | `"completed"` | The full pipeline finished successfully |
| `status` | `"completed"` | The guarded prediction pipeline finished successfully |
| `confidence_interval` | object | Model output includes uncertainty bounds |
| `data_provenance` | non-empty array | Output is grounded in validated sources |
| `explanation_artifact` | object | Explainability evidence was attached |

If any guard fails, the response will show `escalation_reason` set and `status` will not be `"completed"`.

**Step 3 - Test webhook guardrails (optional)**

The webhook guard validates HMAC-SHA256 signatures for asynchronous ingestion events. It accepts the event but does **not** run the prediction graph synchronously - that requires an ARQ worker.

```bash
# Generate a signed request (Python required)
python3 -c "
import hmac, hashlib, json, time, secrets

secret = '\$(kubectl get secret agropredict-ai-backend-secret -o jsonpath={.data.BACKEND_WEBHOOK_SHARED_SECRET} | base64 -d)'
event = {'event_id': secrets.token_hex(8), 'source_id': 'weather-feed-42', 'tenant_id': 'tenant-alpha', 'team_id': 'team-core', 'summary': 'Weather feed refresh'}
body = json.dumps(event)
timestamp = int(time.time())
payload = f'{timestamp}.{body}'
sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
print(f'curl -s -X POST http://127.0.0.1:18000/api/v1/webhooks/ingestion \\')
print(f'  -H \"Content-Type: application/json\" \\')
print(f'  -H \"X-Hub-Signature-256: sha256={sig}\" \\')
print(f'  -H \"X-Atlassian-Webhook-Timestamp: {timestamp}\" \\')
print(f'  -d \"{body}\"')
"
```

Expected response: `{"event_id": "...", "accepted": true, "deduplicated": false}`

If you get `{"detail": "invalid_signature"}`, the signature was computed incorrectly. The signing payload must be `"{timestamp}.{body}"` (dot-separated), not just the body.

#### Quick test with Makefile

```bash
# Requires port-forward running in another terminal
make smoke-test
```

This runs the health check and simulate workflow automatically.

#### Useful Makefile targets

```bash
make help               # List all available targets
make check-prereqs      # Verify tools and Minikube status
make minikube-status    # Show pod status
make minikube-logs      # Tail backend logs
make generate-fernet-key # Print a new Fernet encryption key
```

#### Tear down

```bash
make minikube-delete
minikube stop
```

## Troubleshooting

### Docker Compose (Option A)

#### PostgreSQL or Redis fails to start

Check the container status:

```bash
make local-status
make local-logs
```

Common causes:

| Error | Fix |
|---|---|
| Port `5432` already in use | Stop the conflicting service or change the host port in `docker-compose.yml` |
| Port `6379` already in use | Stop the conflicting service or change the host port in `docker-compose.yml` |
| `pgvector` extension missing | Ensure the image is `pgvector/pgvector:pg16` |

#### Backend cannot connect to database or Redis

If you see `configured: false` for database or Redis in the health check, verify the containers are running and healthy:

```bash
docker compose ps
```

The `dev-backend` target auto-wires connection URLs only if the environment variables are **not** already set. If you previously exported custom values, unset them first:

```bash
unset BACKEND_DATABASE_URL BACKEND_REDIS_URL
make dev-backend
```

### Minikube (Option B)

#### Curl returns empty response or "Connection refused"

The port-forward is not running or has stopped. Start it in a separate terminal:

```bash
make port-forward
# or: kubectl port-forward svc/backend 18000:8000
```

If you restarted the deployment, the port-forward dies. Kill it and start a new one.

#### Backend pod CrashLoopBackOff

Check the logs:

```bash
kubectl logs -l app=backend --tail=50
```

Common causes:

| Error | Fix |
|---|---|
| `Encryption is not configured` | Run `make minikube-secrets` and redeploy |
| `Webhook shared secret is not configured` | Run `make minikube-secrets` and redeploy |
| `Connection refused` to database | Database URL is missing or PostgreSQL is not running (non-fatal for local dev) |

If you changed the secret after deploying, restart the pods:

```bash
kubectl rollout restart deployment/backend
```

#### Pod stuck in ImagePullBackOff

The images must be built inside Minikube's Docker daemon:

```bash
minikube image build -t langgraph-backend:latest ./backend
minikube image build -t langgraph-frontend:latest ./frontend
kubectl rollout restart deployment/backend deployment/frontend
```

#### Port-forward fails

Make sure the pods are running first:

```bash
kubectl get pods
# Both should show 1/1 Running
```

If a port-forward is already running on that port, kill it:

```bash
lsof -ti:18000 | xargs kill 2>/dev/null
lsof -ti:18080 | xargs kill 2>/dev/null
```

#### Cannot access services via NodePort URL

Minikube with the Docker driver does not expose NodePort services on the host. The URLs like `http://192.168.49.2:30800` will not work from your browser. Use `make port-forward` or `minikube service` instead (see "Access the services" above).

#### Health check shows "not configured" for database/Redis

This is expected for local Minikube without PostgreSQL or Redis deployed. The backend starts successfully and serves API requests. Persistence-dependent features (checkpoints, queues, audit) will not function until you deploy those services.

### Common to both options

#### Webhook returns `invalid_signature`

The HMAC signature must be computed over the string `"{timestamp}.{body}"` (dot-separated), not just the body. The `X-Hub-Signature-256` header value must be prefixed with `sha256=`. The timestamp in the header must match the one used in the signature payload.

## Agent observability with LangSmith

LangSmith tracing is disabled by default. The setup differs by environment.

### Local development (Docker Compose)

Export the variables before starting the backend:

```bash
export LANGCHAIN_TRACING_V2=true
export LANGSMITH_API_KEY=<your-LANGSMITH_API_KEY>
export LANGSMITH_PROJECT=agropredict-ai-local
make dev-backend
```

### Local Minikube

Enable LangSmith by setting the environment variables on the running deployment:

```bash
kubectl set env deployment/backend \
  LANGCHAIN_TRACING_V2=true \
  LANGSMITH_API_KEY=<your-LANGSMITH_API_KEY> \
  LANGSMITH_PROJECT=agropredict-ai-local
```

### Staging and production (Helm + Vault)

Store the API key in Vault once. External Secrets Operator syncs it into the cluster automatically (refreshes every hour).

```bash
vault kv patch kv/agropredict-ai/runtime \
  langsmith_api_key=<your-LANGSMITH_API_KEY>
```

Then deploy with the environment-specific values file:

```bash
# Staging
helm upgrade --install agropredict-ai ./helm \
  -f helm/values.yaml \
  -f helm/values-staging.yaml

# Production
helm upgrade --install agropredict-ai ./helm \
  -f helm/values.yaml \
  -f helm/values-prod.yaml
```

Each file sets `langsmith.enabled: true` and a dedicated project name (`agropredict-ai-staging` / `agropredict-ai-prod`) so traces are separated by environment in the LangSmith UI.

For a self-hosted LangSmith instance add `langsmith.endpoint: "https://langsmith.example.internal"` to your values override.

> **Air-gapped deployments:** LangSmith is permanently disabled in `values-air-gapped.yaml`. The pods set `DO_NOT_TRACK=1` and `LANGCHAIN_TRACING_V2=false` to suppress PostHog network flush errors from the `langsmith` transitive dependency.

## Development commands

```bash
# Backend lint
uv run --project backend ruff check backend/src backend/tests

# Backend tests
uv run --project backend pytest

# Frontend test
npm run --prefix frontend test -- --run

# Frontend build
npm run --prefix frontend build
```
