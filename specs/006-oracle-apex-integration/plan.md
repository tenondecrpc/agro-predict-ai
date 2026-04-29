# Implementation Plan: Oracle APEX Integration

**Branch**: `006-oracle-apex-integration` | **Date**: 2026-04-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-oracle-apex-integration/spec.md`

## Summary

Build an Oracle APEX adapter using the API Gateway pattern. APEX runs on Oracle DB and communicates with AgroPredict AI via REST APIs. Read-only data sync pulls data from APEX into PostgreSQL. Audited write-back sends prediction results to APEX with explicit operator approval. Circuit breaker protects the integration.

## Technical Context

**Language/Version**: Python 3.12+  
**Primary Dependencies**: FastAPI, httpx, tenacity  
**Storage**: PostgreSQL (AgroPredict), Oracle DB (APEX)  
**Integration**: REST API via Oracle APEX / Oracle REST Data Services (ORDS)  
**Testing**: pytest, unittest.mock  

## Architecture Decisions

1. **API Gateway Pattern**: APEX and AgroPredict communicate via HTTP REST, not direct DB links.
2. **Read-only adapter**: APEX exposes REST endpoints for data export; AgroPredict polls/ingests.
3. **Write-back via API**: AgroPredict exposes `/api/v1/apex/writeback` which APEX calls (or AgroPredict pushes to APEX webhook).
4. **Circuit breaker**: Tenacity + custom state machine for Oracle APEX connection health.
5. **Audit trail**: Every write-back is logged with prediction_id, user, timestamp, data.

## Constitution Check

| Principle | Check | Notes |
|-----------|-------|-------|
| I. Agent-First Orchestration | PASS | Integration is adapter pattern, not agent graph |
| II. Data-Driven Decisions | PASS | All data validated before ingestion |
| III. Test-First Validation | PASS | TDD enforced |
| IV. Observability & Explainability | PASS | Audit logs, circuit breaker state |
| V. Resilience & Graceful Degradation | PASS | Circuit breaker, retry, degradation |
