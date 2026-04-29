---
title: "feat: Oracle APEX Procurement Copilot Integration"
type: feat
status: active
date: 2026-04-29
origin: specs/021-procurement-apex-application/spec.md
---

# feat: Oracle APEX Procurement Copilot Integration

## Overview

Wire the existing FastAPI procurement backend (specs 018-020, scaffolded under [backend/src/backend/procurement/](backend/src/backend/procurement/)) to a new Oracle APEX buyer-facing application that satisfies the Hackathon "Copiloto Inteligente de Compras" challenge. APEX captures purchase requests and quotations, calls the procurement REST API for AI extraction, comparison, recommendation, and negotiation drafting, and renders results to buyers. The repo already contains an end-to-end APEX build guide under [operations/apex/](operations/apex/) and matching REST contracts; this plan executes that guide and packages the deliverable.

## Problem Frame

The hackathon judging rubric (see provided PDFs) is weighted 60% on the APEX application itself: functionality of the buy-request -> quotations -> compare -> recommend -> negotiate flow (15%), AI integration relevance (15%), recommendation quality (10%), visual design (10%), navigation (10%). The remaining 40% is the pitch. The repo is currently a backend-and-docs codebase with no live APEX artifact. We must:

1. Run the backend with seed data and expose it on a reachable URL (free APEX cloud cannot reach localhost).
2. Build the 6-page APEX application against the documented REST endpoints.
3. Ensure the AI flow (LLM extractor, recommender, negotiator) actually returns useful output during the demo, with rule-based fallback for air-gapped/no-LLM mode.
4. Package the APEX export and rehearse the demo.

## Requirements Trace

- R1. Register purchase requests, suppliers, and quotations via APEX UI (rubric: Funcionalidad principal; spec 021 US1; spec 018 FR-001..010).
- R2. Compare offers side-by-side with currency normalization and clear "best on X" highlighting (rubric: Calidad de recomendacion; spec 021 US2; spec 019).
- R3. Generate an AI recommendation with justification grounded in price, lead time, warranty, payment terms, anomaly score, and weather/FX context (rubric: Integracion IA + Calidad recomendacion; constitution Data-Driven Decisions).
- R4. Generate an editable AI negotiation message; allow buyer to send via `manual_copy` channel at minimum (rubric: Integracion IA; spec 020).
- R5. Visible audit trail per request (spec 021 US4; constitution observability).
- R6. APEX UI must be navigable end-to-end without coaching (rubric: Usabilidad y navegacion; Diseno visual).
- R7. Packaged as installable APEX export `.sql` plus a setup README (spec 021 FR-001; rubric: Factibilidad tecnica).

## Scope Boundaries

- The buyer-facing UI lives in APEX. The existing Vite + React frontend under [frontend/](frontend/) is not retargeted in this plan.
- Procurement state lives in Postgres via the FastAPI backend. APEX has no procurement tables of its own (see [operations/apex/README.md](operations/apex/README.md)). The `006-oracle-apex-integration` write-back path is out of scope for this MVP; APEX consumes the backend REST API directly.
- Authentication is mocked in APEX via a role selector (see [operations/apex/04_pages/01_login.md](operations/apex/04_pages/01_login.md)). Real SSO is out of scope.
- No retargeting to a customer-owned APEX instance. The deliverable is the export `.sql` plus the build guide.

### Deferred to Separate Tasks

- Audited write-back to APEX-managed tables (per spec 006): future iteration once a customer-owned APEX instance with target tables exists.
- Production-grade auth and tenant entitlement enforcement at the APEX edge: deferred; demo runs against `tenant-yguazu` / `team-compras`.
- Multi-tenant data export with retention and deletion policy enforcement (spec 021 US4 FR for export): deferred to post-hackathon parity work.

## Context & Research

### Relevant Code and Patterns

- Backend procurement router and contracts: [backend/src/backend/procurement/api.py](backend/src/backend/procurement/api.py), models in [backend/src/backend/procurement/models.py](backend/src/backend/procurement/models.py), agent schemas in [backend/src/backend/procurement/agents/schemas.py](backend/src/backend/procurement/agents/schemas.py).
- Orchestrator (LangGraph procurement pipeline): [backend/src/backend/procurement/orchestrator.py](backend/src/backend/procurement/orchestrator.py).
- LLM agents (extractor, comparator, recommender, negotiator) with rule-based fallbacks: [backend/src/backend/procurement/agents/](backend/src/backend/procurement/agents/).
- Demo seed and fixtures (8 suppliers, 5 requests, 15 quotations, 157 history rows): [backend/src/backend/procurement/fixtures/seed.py](backend/src/backend/procurement/fixtures/seed.py).
- APEX build guide (authoritative for this plan): [operations/apex/](operations/apex/), specifically [01_prerequisites.md](operations/apex/01_prerequisites.md), [02_workspace_setup.md](operations/apex/02_workspace_setup.md), [03_rest_sources.md](operations/apex/03_rest_sources.md), the [04_pages/](operations/apex/04_pages/) folder, [05_demo_script.md](operations/apex/05_demo_script.md), and [06_export_checklist.md](operations/apex/06_export_checklist.md).
- OpenAPI contract: [contracts/openapi/openapi-v1.json](contracts/openapi/openapi-v1.json) - confirms all 16 procurement endpoints already exposed under `/api/v1/procurement/`.
- Spec 021 acceptance scenarios and edge cases: [specs/021-procurement-apex-application/spec.md](specs/021-procurement-apex-application/spec.md).
- App startup with healthz: [backend/src/backend/app.py](backend/src/backend/app.py) line 170.

### Institutional Learnings

- The `operations/apex/README.md` explicitly chose "no APEX-side procurement tables, APEX is a pure consumer". This avoids schema duplication and sync logic for the hackathon. Honor that boundary.
- Cross-tenant lookups in the backend return 404 not 403 to avoid existence leaks ([api.py](backend/src/backend/procurement/api.py)). APEX must always pass `tenant_id` on every call.
- The seed re-seeds the `tenant-yguazu` tenant; safe to rerun if state drifts during rehearsal.

### External References

- Hackathon rubric (provided PDFs): 60% APEX app, 40% pitch. Strong incentive to favor demo polish on Page 6 (compare/recommend/negotiate) over breadth of features.
- APEX Free Workspace: https://apex.oracle.com signup is instant; default theme `Vita - Light` is acceptable.

## Key Technical Decisions

- **APEX as pure REST consumer.** No APEX tables, no write-back. Rationale: matches existing build guide, removes a class of failure modes for the hackathon, and the rubric scores the user-facing flow regardless of where state lives. Spec 021 originally allowed APEX-managed tables; we deliberately deviate from that for this iteration and capture it as a Deferred item.
- **Mocked role selector, no real auth.** Rationale: hackathon scope; rubric does not require auth. APEX `G_TENANT_ID`, `G_TEAM_ID`, `G_USER_ID` items hold the demo identity and are passed as query parameters to the backend.
- **ngrok for backend exposure.** Free APEX in Oracle Cloud cannot reach `localhost`. Rationale: lowest-friction tunnel; the build guide already specifies it. Fallback: any HTTPS tunnel (Cloudflare Tunnel, Tailscale Funnel) works since the backend has no auth in dev.
- **LLM degraded mode is first-class.** When the LLM provider is unreachable or disabled, the recommender returns a rule-based recommendation with `degradation_flags: ["llm_disabled"]` and the UI surfaces a banner. Rationale: constitution requires graceful degradation; air-gapped profile must work; demo cannot fail because of a flaky LLM key.
- **Page 6 first.** Build [04_pages/06_compare_recommend.md](operations/apex/04_pages/06_compare_recommend.md) as the first page after the shell, then backfill 1-5. Rationale: this page demonstrates the entire AI value proposition; if time runs short, demo can survive on seed data plus Page 6 alone.
- **Seed data is the demo.** The 5-request seed contains the urea-for-soja-26/27 hero scenario. Rationale: 4-hour APEX build budget plus rehearsal leaves no room for live data entry as the primary demo path.

## Open Questions

### Resolved During Planning

- *Should APEX manage its own procurement tables (per spec 021)?* No. We are following [operations/apex/README.md](operations/apex/README.md) which already pivoted to "REST consumer only". This is the simpler and more reliable demo path.
- *Which LLM provider is wired up?* The agents in [agents/](backend/src/backend/procurement/agents/) accept any compatible client (Anthropic / OpenAI). Provider selection is a deployment-time env-var concern, not a planning blocker.
- *Where does the export live?* `operations/apex/agrobuy.sql` is the target path, plus a SHA-256 alongside.

### Deferred to Implementation

- Exact ngrok URL each session: substituted into APEX `BACKEND_URL` substitution string at start of each demo session. Treat as a runbook step, not a plan decision.
- Whether to enable email outbox channel (`email_outbox`) for the negotiator: depends on whether SMTP credentials are configured at demo time. `manual_copy` always works; default to that.
- Final visual polish (icons, header copy, Spanish microcopy fine-tuning): execution-time discovery during rehearsal.

## Implementation Units

- [ ] **Unit 1: Stand up backend + seed data + tunnel**

**Goal:** Backend reachable from APEX cloud with full demo seed loaded.

**Requirements:** R1, R3.

**Dependencies:** None.

**Files:**
- Modify (config only): `.env.local` (local secrets, not committed) following [.env.example](.env.example)
- Verify: [backend/src/backend/procurement/fixtures/seed.py](backend/src/backend/procurement/fixtures/seed.py) runs cleanly
- Reference: [operations/apex/01_prerequisites.md](operations/apex/01_prerequisites.md)

**Approach:**
- `docker compose --profile worker up -d` to start Postgres + Redis.
- Source local env, run `uv run --project backend python -m backend.procurement.fixtures.seed`, then `uv run --project backend uvicorn backend.app:app --host 0.0.0.0 --port 8000`.
- `ngrok http 8000` in a second terminal; capture the HTTPS URL into `BACKEND_PUBLIC_URL`.
- Smoke-test `/healthz` and `/api/v1/procurement/requests?tenant_id=tenant-yguazu` through the public URL.

**Verification:**
- `curl $BACKEND_PUBLIC_URL/healthz` returns `{"status": "ok"}` with database and redis configured.
- `curl "$BACKEND_PUBLIC_URL/api/v1/procurement/requests?tenant_id=tenant-yguazu"` returns the 5 seeded requests.
- A spot-call to `POST /api/v1/procurement/requests/{id}/recommend` against a seeded request returns a `Recommendation` payload (LLM or rule-based fallback both acceptable; `degradation_flags` if applicable).

**Test scenarios:**
- Happy path: backend boots, seed populates 8 suppliers / 5 requests / 15 quotations, list endpoints return them.
- Error path: rerun seed twice in a row, second run succeeds (idempotent re-seed of `tenant-yguazu`).
- Integration: `POST /requests/{id}/recommend` end-to-end exercises orchestrator + scoring + agents and returns a structured recommendation including `composite_score`, `decision_band`, `justification`.

---

- [ ] **Unit 2: APEX workspace, app shell, and global state**

**Goal:** Empty APEX application with global items, substitution strings, and theme matching the demo.

**Requirements:** R6, R7.

**Dependencies:** Unit 1 (need `BACKEND_PUBLIC_URL` for substitution).

**Files:**
- Reference: [operations/apex/02_workspace_setup.md](operations/apex/02_workspace_setup.md)
- Output (created in APEX, exported in Unit 8): `operations/apex/agrobuy.sql`

**Approach:**
- Sign in to apex.oracle.com workspace `AGROBUY`.
- Create application "AgroBuy - Copiloto Compras Agro", theme `Vita - Light`.
- Create application items: `G_TENANT_ID`, `G_TEAM_ID`, `G_USER_ID`, `G_USER_NAME`, `G_ROLE`, `G_BACKEND_URL`.
- Create substitution strings `BACKEND_URL`, `TENANT_ID`, `TEAM_ID`.
- Delete the default home page; pages 1-6 are added in subsequent units.

**Verification:**
- App renders an empty shell at the workspace URL.
- Substitution `&BACKEND_URL.` resolves to the ngrok host in a test region.

**Test scenarios:**
- Happy path: load the empty app and confirm theme + global items are present.
- Edge case: rotate `BACKEND_URL` substitution to a bogus value; pages built later must surface a friendly error rather than crash (validated in Unit 9 rehearsal).

---

- [ ] **Unit 3: REST Data Sources for all 16 procurement endpoints**

**Goal:** APEX REST Data Sources (RDS) wired to every backend procurement route.

**Requirements:** R1, R2, R3, R4, R5.

**Dependencies:** Unit 2.

**Files:**
- Reference: [operations/apex/03_rest_sources.md](operations/apex/03_rest_sources.md)
- Reference (contract): [contracts/openapi/openapi-v1.json](contracts/openapi/openapi-v1.json)

**Approach:**
- Create one Generic JSON RDS per row in the inventory table in [03_rest_sources.md](operations/apex/03_rest_sources.md): `RDS_REQUESTS_LIST`, `RDS_REQUEST_DETAIL`, `RDS_REQUEST_CREATE`, `RDS_REQUEST_TRANSITION`, `RDS_REQUEST_RECOMMEND`, `RDS_QUOTATIONS_LIST`, `RDS_QUOTATION_DETAIL`, `RDS_QUOTATION_CREATE`, `RDS_QUOTATION_EXTRACT`, `RDS_QUOTATION_NEGOTIATE`, `RDS_SUPPLIERS_LIST`, `RDS_SUPPLIER_DETAIL`, `RDS_SUPPLIER_CREATE`, `RDS_WEATHER_RISK`, `RDS_FX_USD_PYG`, `RDS_AUDIT`.
- Configure path bind variables (`:request_id`, `:quotation_id`, `:supplier_id`) and static defaults `tenant_id=&TENANT_ID.` and `team_id=&TEAM_ID.` per the per-source tips.
- Mark POST sources operating on side-effecting routes (`/transition`, `/recommend`, `/extract`, `/negotiate`) as `Execute` rather than `Insert Row`.

**Verification:**
- For each RDS, click Discover and confirm APEX renders sample columns.
- Run a one-off "Test Operation" on `RDS_REQUESTS_LIST` and `RDS_REQUEST_RECOMMEND` against a seeded request id; both return data.

**Test scenarios:**
- Happy path: list RDS returns 5 requests for `tenant-yguazu`.
- Edge case: cross-tenant call (`tenant_id=tenant-other`) returns 404 (existence leak guard); RDS surfaces empty result rather than error.
- Integration: chained `RDS_REQUEST_DETAIL` then `RDS_QUOTATIONS_LIST` against the same `request_id` agrees on counts.

---

- [ ] **Unit 4: Page 6 - Comparar / Recomendar / Negociar (star page)**

**Goal:** The single highest-rubric-impact page: side-by-side comparison, AI recommendation card, AI negotiation drafter.

**Requirements:** R2, R3, R4.

**Dependencies:** Unit 3.

**Files:**
- Reference (authoritative): [operations/apex/04_pages/06_compare_recommend.md](operations/apex/04_pages/06_compare_recommend.md)

**Approach:**
- Page 6 with hidden item `P6_REQUEST_ID` from URL plus the hidden state items listed in the page guide (`P6_RECOMMENDATION_JSON`, `P6_RECOMMENDED_QUOTATION_ID`, `P6_DECISION_BAND`, `P6_REASONING_MARKDOWN`, etc.).
- Region 1 Interactive Report bound to `RDS_QUOTATIONS_LIST` with column highlights (best price, fastest delivery, anomaly >= 0.6).
- Region 2 Recommendation card driven by `BTN_RECOMMEND` -> calls `RDS_REQUEST_RECOMMEND` -> hydrates hidden state items -> conditional region renders justification, decision band, composite score, weather risk, FX rate, and a `degradation_flags` banner when the response carries `llm_disabled` or `policy_violation`.
- Region 3 Negotiation drafter: select target supplier (defaults to recommended), pick objective from a fixed list (`lower_price`, `extend_warranty`, `faster_delivery`, `flexible_payment`), button calls `RDS_QUOTATION_NEGOTIATE`, displays editable textarea, action buttons `Copiar` (manual_copy) and `Enviar email` (email_outbox, hidden when not configured).

**Patterns to follow:**
- Highlights and pill renderers: same Interactive Report styling used in Page 4.
- Substitution-driven backend URL: every dynamic action uses `&BACKEND_URL.` not hardcoded host.
- No color-only state: every highlight has an icon + text label per spec 021 accessibility constraint.

**Test scenarios:**
- Happy path: open `f?p=APP:6:::::P6_REQUEST_ID:<seeded-id>`, click Recomendar, recommendation card renders with justification text, composite score, and decision band within ~5 seconds.
- Happy path: click Generar mensaje for the recommended supplier with objective `lower_price`; an editable Spanish draft appears.
- Edge case: response carries `degradation_flags: ["llm_disabled"]`; banner reads "Recomendacion basada en reglas (LLM no disponible)" and the recommendation still renders.
- Edge case: anomaly_score >= 0.6 row shows amber background plus warning icon plus "Anomalia" label.
- Error path: backend returns 500; page shows a non-cryptic error region and the comparison table still renders from the cached list.
- Integration: Copiar action records a `manual_copy` audit event visible in `RDS_AUDIT`.

**Verification:**
- Manual click-through on the urea-for-soja-26/27 seeded request renders all three regions cleanly and the recommendation matches the rule-based scoring even with the LLM disabled.

---

- [ ] **Unit 5: Pages 1-2 - Login mock and Inbox**

**Goal:** Buyer entry point and request list.

**Requirements:** R1, R6.

**Dependencies:** Unit 3 (RDS_REQUESTS_LIST). Independent of Unit 4.

**Files:**
- Reference: [operations/apex/04_pages/01_login.md](operations/apex/04_pages/01_login.md), [operations/apex/04_pages/02_inbox.md](operations/apex/04_pages/02_inbox.md)

**Approach:**
- Page 1: Static role selector (`solicitante`, `comprador`, `aprobador`, `director`); on submit sets `G_USER_ID`, `G_USER_NAME`, `G_ROLE`; redirects to Page 2.
- Page 2: Interactive Report from `RDS_REQUESTS_LIST` with status pill, urgency badge, and link to Page 4 detail. Filters: status, my-requests-only.

**Test scenarios:**
- Happy path: pick `comprador` role, land on Inbox showing 5 requests.
- Edge case: filter by status `ready_for_review` returns only matching seed rows.
- Integration: clicking a row routes to Page 4 with `P4_REQUEST_ID` populated.

**Verification:**
- Both pages load in under 2 seconds against ngrok-hosted backend.

---

- [ ] **Unit 6: Pages 3-4 - Create request and Request detail**

**Goal:** Capture path for new requests and per-request supplier/quotation list.

**Requirements:** R1, R5, R6.

**Dependencies:** Unit 3.

**Files:**
- Reference: [operations/apex/04_pages/03_create_request.md](operations/apex/04_pages/03_create_request.md), [operations/apex/04_pages/04_request_detail.md](operations/apex/04_pages/04_request_detail.md)

**Approach:**
- Page 3: form bound to `RDS_REQUEST_CREATE` (item description, quantity, unit, target delivery, budget cap, currency). On success redirect to Page 4 with the new id.
- Page 4: header card from `RDS_REQUEST_DETAIL`, quotations report from `RDS_QUOTATIONS_LIST`, suppliers picker from `RDS_SUPPLIERS_LIST`, transition button to `ready_for_review` calling `RDS_REQUEST_TRANSITION`, link to Page 5 to upload a quotation, link to Page 6 to compare.

**Test scenarios:**
- Happy path: create a new request, land on Page 4 with empty quotations list.
- Edge case: missing required fields trigger inline validation, no backend call.
- Edge case: transition to `ready_for_review` with zero quotations; backend returns 422 (data quality gate); APEX surfaces the failure reason.
- Integration: after creating + adding two quotations + transitioning, Page 6 renders comparison correctly.

**Verification:**
- A from-scratch request flows through Pages 3 -> 4 -> 5 -> 4 -> 6 without errors.

---

- [ ] **Unit 7: Page 5 - Upload quotation with AI extractor**

**Goal:** Quotation entry with optional LLM extraction from raw text.

**Requirements:** R1, R3.

**Dependencies:** Unit 3, Unit 6 (entry point lives on Page 4).

**Files:**
- Reference: [operations/apex/04_pages/05_upload_quotation.md](operations/apex/04_pages/05_upload_quotation.md)

**Approach:**
- Two-mode form: structured manual fields, plus a "Pegar texto de la cotizacion" textarea. The Extraer con IA button calls `RDS_QUOTATION_EXTRACT` and pre-populates the structured fields from the response. Save button calls `RDS_QUOTATION_CREATE`.

**Test scenarios:**
- Happy path: paste sample quotation text, extractor returns supplier name, total, currency, lead time; user saves; new row appears on Page 4.
- Edge case: extractor returns partial fields (low confidence); UI flags `estimated` fields visibly.
- Error path: extractor times out / returns degradation flag; UI offers manual entry without losing the textarea content.

**Verification:**
- One quotation saved via extractor path and one via manual path both appear on Page 4 and feed into Page 6 comparison.

---

- [ ] **Unit 8: Demo data, rehearsal, and APEX export**

**Goal:** Hackathon-ready artifact: rehearsed demo plus exportable `.sql`.

**Requirements:** R6, R7.

**Dependencies:** Units 4-7.

**Files:**
- Reference: [operations/apex/05_demo_script.md](operations/apex/05_demo_script.md), [operations/apex/06_export_checklist.md](operations/apex/06_export_checklist.md)
- Output: `operations/apex/agrobuy.sql`, `operations/apex/agrobuy.sql.sha256`

**Approach:**
- Re-run the seed; walk the 90-second demo arc from [05_demo_script.md](operations/apex/05_demo_script.md) at least twice end-to-end (Inbox -> Detail -> Compare -> Recommend -> Negotiate -> Copy).
- Capture screenshots for the pitch deck (compare table with highlights, recommendation card, negotiation draft).
- Export the APEX application via App Builder -> Export -> Application Export, save to `operations/apex/agrobuy.sql`, record SHA-256.
- Update [operations/apex/README.md](operations/apex/README.md) install instructions block if anything diverged during build.

**Test scenarios:**
- Happy path: full demo arc completes within 90 seconds without backend errors.
- Edge case: simulate ngrok dropping mid-demo; substitution swap to a fresh URL recovers without rebuild.
- Edge case: disable the LLM provider env var; recommendation still renders with rule-based fallback and the degradation banner.

**Verification:**
- Two consecutive clean demo runs.
- `agrobuy.sql` re-imports into a fresh APEX workspace and the smoke-test path (Inbox -> Compare on a seeded request) works against a new ngrok URL.

---

- [ ] **Unit 9: Pitch deck assets and verification matrix**

**Goal:** Pitch-side deliverables aligned to the 40% rubric (pertinencia, claridad, innovacion, factibilidad, impacto).

**Requirements:** R6, R7.

**Dependencies:** Unit 8 (need final screenshots and demo video).

**Files:**
- Create: `docs/pitch/agrobuy-pitch-outline.md` (talking points only, no deck binary in repo)
- Create: `docs/pitch/rubric-traceability.md` mapping each rubric criterion to a feature, code path, and demo timestamp

**Approach:**
- Pitch outline covers: problem (compras manuales), solution (APEX copilot), demo arc, factibilidad (uses customer-owned APEX, no vendor SaaS, air-gapped degradation supported), impacto (time saved, decision traceability via audit), innovacion (rule-based + LLM dual-mode recommender).
- Traceability matrix lists the 10 rubric rows and points each to evidence (page, endpoint, spec, demo cue).

**Test scenarios:**
- Test expectation: none -- documentation only.

**Verification:**
- A non-author skim of the outline can answer "what does this product do, how, and why does it matter" in under 3 minutes.

## System-Wide Impact

- **Interaction graph:** APEX -> ngrok -> FastAPI procurement router -> orchestrator -> {scoring, ML, LLM agents, weather, FX} -> Postgres. No callbacks back to APEX (no write-back in this iteration).
- **Error propagation:** Backend exceptions become HTTP 4xx/5xx; APEX RDS surfaces them as page error regions. LLM unavailability does not surface as an error - it returns 200 with `degradation_flags`.
- **State lifecycle risks:** APEX free-tier sessions can expire; the seed plus `manual_copy` always work, so a re-login mid-demo is not catastrophic. ngrok URL rotates each session; `BACKEND_URL` substitution must be updated before each demo.
- **API surface parity:** No backend route changes are required. If gaps appear during APEX build, document them as defects against [api.py](backend/src/backend/procurement/api.py) and fix the backend, not APEX-only workarounds.
- **Integration coverage:** Page 6 is the only place where comparator + recommender + negotiator interact end-to-end; rehearsal exercises that path twice.
- **Unchanged invariants:** The constitution's data quality gate, audit trail, tenant isolation, and graceful degradation behaviors remain enforced server-side. APEX cannot bypass them. The existing Vite + React frontend ([frontend/](frontend/)) is unaffected.

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| ngrok URL rotates between sessions and breaks all RDS bindings | All RDS use `&BACKEND_URL.` substitution; updating one app substitution refreshes every page. Documented in demo runbook. |
| LLM provider rate-limits or fails during demo | Rule-based fallback returns a valid recommendation with `degradation_flags`; UI banner makes the mode visible. Air-gapped path tested in Unit 8. |
| Seed drifts after live data entry during rehearsal | Re-run `python -m backend.procurement.fixtures.seed` to wipe and reseed `tenant-yguazu` before each rehearsal. |
| APEX free-tier workspace inactive timeout | Sign in 30 min before pitch; keep app open in a tab; export the `.sql` early as backup. |
| Time pressure forces dropping pages | Build order is Page 6 -> 1 -> 2 -> 4 -> 3 -> 5; demo can survive on Pages 1-2-4-6 alone using seed data (per [operations/apex/README.md](operations/apex/README.md)). |
| Spec 021 originally assumed APEX-managed tables; deviation is unreviewed | Deviation captured under Scope Boundaries / Deferred; not blocking but flagged for post-hackathon spec amendment. |

## Documentation / Operational Notes

- Update [operations/apex/README.md](operations/apex/README.md) only if instructions diverged during build.
- Add a short "How to install the APEX export" note inside [operations/apex/06_export_checklist.md](operations/apex/06_export_checklist.md) if the existing one omits the substitution-string update step.
- Record demo runbook as a fresh file `operations/apex/RUNBOOK.md` covering: start backend -> seed -> ngrok -> update `BACKEND_URL` substitution -> sign in -> walk arc.

## Sources & References

- **Origin document:** [specs/021-procurement-apex-application/spec.md](specs/021-procurement-apex-application/spec.md)
- Related backend specs: [specs/018-procurement-domain/](specs/018-procurement-domain/), [specs/019-procurement-decision-pipeline/](specs/019-procurement-decision-pipeline/), [specs/020-procurement-negotiation-assistant/](specs/020-procurement-negotiation-assistant/)
- Related code: [backend/src/backend/procurement/](backend/src/backend/procurement/), [backend/src/backend/app.py](backend/src/backend/app.py)
- APEX build guide: [operations/apex/](operations/apex/)
- API contract: [contracts/openapi/openapi-v1.json](contracts/openapi/openapi-v1.json)
- Hackathon rubric and problem statement: provided PDFs (Métricas de Evaluación, Problemática)
