# AgroBuy on Oracle APEX - Build Guide

This is the buyer-facing UI for the AgroBuy procurement copilot
(spec 021). It lives in Oracle APEX, consumes the FastAPI backend
through REST Data Sources, and renders purchase requests, quotations,
comparisons, AI recommendations, and negotiation messages.

## Architecture

```
[ APEX pages ]  --REST-->  [ FastAPI backend ]  --SQL-->  [ Postgres ]
       ^                          |
       |                          +--HTTP--> Open-Meteo / open.er-api.com
       |                          +--LLM--> Anthropic / OpenAI compatible
       |
   Buyer (cooperative analyst)
```

There are **no APEX-side procurement tables**. APEX is a pure
consumer of the backend REST API. State lives in Postgres. This is
deliberate: zero schema duplication, zero sync logic, no write-back.

## Build order

1. [01_prerequisites.md](01_prerequisites.md) - Account, ngrok, seed.
2. [02_workspace_setup.md](02_workspace_setup.md) - APEX workspace and app shell.
3. [03_rest_sources.md](03_rest_sources.md) - REST Data Sources for every backend endpoint.
4. [04_pages/](04_pages/) - Page-by-page build instructions:
   - [01_login.md](04_pages/01_login.md) - Mock role selector
   - [02_inbox.md](04_pages/02_inbox.md) - Lista de solicitudes
   - [03_create_request.md](04_pages/03_create_request.md) - Nueva solicitud
   - [04_request_detail.md](04_pages/04_request_detail.md) - Detalle + cotizaciones
   - [05_upload_quotation.md](04_pages/05_upload_quotation.md) - Cargar cotizacion (extractor IA)
   - [06_compare_recommend.md](04_pages/06_compare_recommend.md) - **Star page**
5. [05_demo_script.md](05_demo_script.md) - 90-second demo arc.
6. [06_export_checklist.md](06_export_checklist.md) - Pre-demo verification + export.

## Estimated build time

| Page | Time | Priority |
|---|---|---|
| Workspace + REST sources | 30 min | must |
| P1 Login | 10 min | must |
| P2 Inbox | 30 min | must |
| P3 Create request | 30 min | must |
| P4 Request detail | 40 min | must |
| P5 Upload quotation | 40 min | must |
| P6 Compare / Recommend / Negotiate | 60 min | must (star page) |
| Demo rehearsal | 20 min | must |
| **TOTAL** | **~4 hours** | |

If you have less time, ship pages 1-2-4-6 first; demo can survive
without Create / Upload pages by relying on the seed data alone.

## Contracts at a glance

The backend exposes these endpoints under `/api/v1/procurement/`:

| Method | Path | Purpose |
|---|---|---|
| POST | /requests | Create purchase request |
| GET | /requests | List purchase requests |
| GET | /requests/{id} | Get a request |
| POST | /requests/{id}/transition | Move state (draft -> ready_for_review) |
| GET | /requests/{id}/quotations | List quotations of a request |
| POST | /requests/{id}/recommend | **Run the full AI pipeline** |
| POST | /quotations | Upload a structured quotation |
| GET | /quotations/{id} | Get a quotation |
| POST | /quotations/extract | LLM extractor (raw text -> structured) |
| POST | /quotations/{id}/negotiate | LLM negotiator (draft email) |
| POST | /suppliers | Register a supplier |
| GET | /suppliers | List suppliers |
| GET | /suppliers/{id} | Get a supplier |
| GET | /weather/risk | Open-Meteo weather risk per department |
| GET | /fx/usd_pyg | USD/PYG exchange rate |
| GET | /audit | Procurement audit events |

Tenant defaults for the hackathon demo:
- `tenant_id = "tenant-yguazu"`
- `team_id = "team-compras"`

The seed loaded by `python -m backend.procurement.fixtures.seed`
populates 8 suppliers, 5 purchase requests (with the urea-for-soja-26/27
hero scenario), 15 quotations, and 157 supplier history records.
