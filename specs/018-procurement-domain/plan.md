# Implementation Plan: Procurement Domain and Quotation Ingestion

**Branch**: `022-procurement-implementation` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)

## Summary

Add the procurement domain layer (purchase requests, suppliers, quotations,
quotation items, audit events, agro catalog) on top of PostgreSQL with
tenant and team isolation through Row Level Security. Expose CRUD APIs
and a data quality gate that quarantines invalid quotations before any
downstream AI agent reads them.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, SQLAlchemy 2 (sync), Pydantic v2, Alembic
**Storage**: PostgreSQL 16 (existing platform DB; no new datastore)
**Testing**: pytest
**Target Platform**: Linux server (and Windows for local dev)
**Project Type**: Backend service module under `backend/src/backend/procurement/`
**Performance Goals**: P95 < 200 ms for `GET /procurement/requests/{id}`
**Constraints**: Tenant + team isolation via RLS, audit on every transition
**Scale/Scope**: Multi-tenant; expected MVP load tens of requests per tenant

## Constitution Check

- **Agent-First Orchestration**: This feature ships data layer only. No new
  agent contracts. Downstream pipeline (`019`) consumes validated quotations.
  PASS.
- **Data-Driven Decisions**: Data quality gate is mandatory before any AI
  agent reads a quotation. Quarantined quotations carry structured
  `quality_flags`. PASS.
- **Test-First Validation**: Tests cover tenant isolation regression,
  validity gate, and currency rejection. PASS.
- **Observability and Explainability**: Every transition emits a row in
  `procurement_audit_events`. PASS.
- **Resilience and Graceful Degradation**: Module degrades to in-memory
  repository when DB is not configured. PASS.
- **Tier 1 Tenant Isolation**: PostgreSQL RLS policies on every procurement
  table. PASS.
- **Tier 1 No New Datastore**: Reuses existing PostgreSQL with expand
  migration. PASS.

## Project Structure

### Documentation (this feature)

```text
specs/018-procurement-domain/
+-- spec.md
+-- plan.md
```

### Source code (repository root)

```text
backend/src/backend/procurement/
+-- __init__.py
+-- models.py                  # Pydantic schemas
+-- data_quality_gate.py       # Validity, currency, units, lead time checks
+-- repository.py              # Postgres + InMemory implementations
+-- service.py                 # Orchestration + audit hooks
+-- api.py                     # FastAPI router /api/v1/procurement/*

backend/alembic/versions/
+-- 20260429_0022_procurement_domain.py

backend/tests/integration/
+-- test_procurement_domain.py # Tenant isolation, quality gate, audit log
```

## Migration Strategy

Single forward migration `20260429_0022_procurement_domain.py` that creates:

- `procurement_purchase_requests`
- `procurement_request_items`
- `procurement_suppliers`
- `procurement_quotations`
- `procurement_quotation_items`
- `procurement_audit_events`
- `procurement_agro_catalog`

All tenant-scoped tables enable RLS with the existing
`app.current_tenant_id()` policy pattern used by spec `006-oracle-apex-integration`.

`procurement_agro_catalog` is global reference data and does not enable RLS
(read-only catalog of agro products and market price bands).

## Out of Scope (deferred to later phases)

- Attachment upload to object storage (Phase 4 reuses existing
  `attachment_ref` field as a free-text URL only).
- LLM extraction of quotations from PDFs (Phase 4, spec 019 / 020).
- Weather and FX signals (Phase 2).
- ML supplier predictor and anomaly detection (Phase 3).
- APEX-side UI (Phase 6, spec 021).
- Tenant retention policy cascade (use existing `010-security-secrets` hooks
  in a follow-up).

## Complexity Tracking

No new datastore. No new orchestration framework. Reuses existing
Postgres + RLS + alembic + FastAPI patterns established by specs
`001-017`.
