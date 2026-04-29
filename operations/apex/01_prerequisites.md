# 01 - Prerequisites

## 1. APEX workspace

Create a free workspace at https://apex.oracle.com (instantaneous):

1. Open https://apex.oracle.com/en/learn/getting-started/
2. Click "Get Started for Free" -> "Request a Free Workspace".
3. Choose:
   - Workspace name: `AGROBUY` (uppercase, no spaces)
   - Schema: same as workspace name
   - Username: `ADMIN`
4. Save the password and the workspace URL. They are emailed to you.
5. Sign in. You should land on the App Builder home.

## 2. Public URL for the backend (ngrok)

APEX free-tier runs in Oracle Cloud and cannot reach `localhost:8000`.
Use ngrok to expose the backend.

```bash
# Install ngrok if you do not have it.
# Windows: choco install ngrok   |  macOS: brew install ngrok

# Authenticate once (free account at https://ngrok.com)
ngrok config add-authtoken <YOUR_TOKEN>

# In a separate terminal, with the backend already running:
ngrok http 8000
```

ngrok prints a forwarding URL like `https://2f1a-190-12-34-56.ngrok-free.app`.
That is your `BACKEND_PUBLIC_URL`. Keep that terminal open during the
demo.

Quick sanity check:

```bash
curl -s "$BACKEND_PUBLIC_URL/healthz" | python -m json.tool
```

You should see `"status": "ok"` and `database`/`redis` configured.

## 3. Backend running with seed data

In yet another terminal:

```bash
cd /c/Users/franc/Desktop/hackaton/agro-predict-ai-main
docker compose --profile worker up -d
set -a; source .env.local; set +a
uv run --project backend python -m backend.procurement.fixtures.seed
uv run --project backend uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

The seed creates the demo dataset (8 suppliers, 5 requests, 15
quotations). Re-run any time you need a clean slate; it wipes and
re-seeds the `tenant-yguazu` tenant.

> Use `--host 0.0.0.0` so ngrok can reach the listener.

## 4. Useful tools to keep open

| Window | Purpose |
|---|---|
| Terminal A | Docker Compose (`docker compose ps`) |
| Terminal B | Backend (`uvicorn backend.app:app ...`) |
| Terminal C | ngrok (`ngrok http 8000`) |
| Browser tab 1 | apex.oracle.com (App Builder) |
| Browser tab 2 | `$BACKEND_PUBLIC_URL/docs` (Swagger UI) for live API testing |
| Browser tab 3 | `$BACKEND_PUBLIC_URL/api/v1/procurement/requests?tenant_id=tenant-yguazu` (sanity check) |

## 5. Known free-tier limits

- APEX free: 100 MB storage, 12-hour idle inactivity timeout.
- ngrok free: rotating URL on each restart. Update REST sources in
  APEX after every restart.
