# Implementation Plan: Oracle APEX to Prediction Input Wiring

**Branch**: `016-apex-prediction-wiring` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)

## Summary

Wire the existing FieldDataResolver into the async ARQ worker path, fix the provenance source_id format, implement proper 503 response when APEX is unavailable, add env var configuration for freshness window and sync timeout, and add missing degradation flags (apex_sync_timeout, apex_circuit_open).

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, ARQ, PostgreSQL 16, Oracle APEX adapter
**Storage**: PostgreSQL (apex_field_records, predictions)
**Testing**: pytest
**Target Platform**: Linux server (Kubernetes)
**Project Type**: Web service (backend API + workers)
**Performance Goals**: Resolver adds < 50ms to prediction path
**Constraints**: Read-only APEX, tenant isolation, staleness handling
**Scale/Scope**: Multi-tenant, per-region field records

## Constitution Check

- **Agent-First Orchestration**: FieldDataResolver runs before graph execution - no change to agent contracts. PASS.
- **Data-Driven Decisions**: APEX data with full provenance chain, staleness flags. PASS.
- **Test-First Validation**: Tests for async path resolver, 503 on APEX down, provenance format. PASS.
- **Observability & Explainability**: Provenance entries with checksum, validation status. PASS.
- **Resilience & Graceful Degradation**: Stale data with warning, circuit breaker skip, fallback behavior. PASS.
- **Oracle APEX read-only**: Resolver never writes to Oracle. PASS.
- **Tenant isolation**: All APEX queries scoped to tenant_id. PASS.

## Project Structure

### Documentation (this feature)

```text
specs/016-apex-prediction-wiring/
├── spec.md              # Feature specification
├── plan.md              # This file
└── tasks.md             # Task list
```

### Source Code (repository root)

```text
backend/src/backend/predictions/
├── field_data_resolver.py   # Modified: fix source_id format, add env vars, degradation flags
├── service.py               # Modified: proper 503 on NoInputDataError
├── api.py                   # Modified: 503 handling for APEX unavailable
backend/src/backend/
├── worker.py                # Modified: wire FieldDataResolver into async path
backend/src/backend/integrations/
└── oracle_apex/
    └── service.py           # Existing: APEXService (no changes needed)
backend/tests/
├── unit/
│   └── test_field_data_resolver.py  # Modified: async path, 503, provenance tests
└── integration/
    └── test_apex_prediction.py      # New: end-to-end APEX wiring tests
```

## Complexity Tracking

No constitution violations. APEX wiring extends existing patterns.
