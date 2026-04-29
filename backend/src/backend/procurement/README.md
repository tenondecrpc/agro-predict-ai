# Procurement Module

Intelligent Purchasing Copilot for Paraguayan agro cooperatives.

## Status

Phase 0 complete: scaffold only. No business logic yet.

## Layout

```
procurement/
├── __init__.py
├── api.py                   # FastAPI router (Phase 1+)
├── models.py                # Pydantic schemas (Phase 1)
├── repository.py            # SQLAlchemy access layer (Phase 1)
├── service.py               # Orchestration facade (Phase 5)
├── data_quality_gate.py     # Spec 018 quality validations (Phase 1)
├── graph.py                 # LangGraph ProcurementGraph (Phase 5)
├── agents/                  # LLM agents: extractor, comparator, recommender, negotiator (Phase 4)
├── scoring/                 # Urgency + Offer scoring + decision matrix (Phase 3)
├── ml/                      # Supplier predictor + anomaly detector (Phase 3)
├── external/                # Open-Meteo + BCP FX fetchers (Phase 2)
└── fixtures/                # Demo data: agro suppliers, history, sample quotations (Phase 7)
```

## Phase progress

See `compras/DEV_PLAN.md` at the repository root for the full plan.

- [x] Phase 0 - Bootstrap
- [ ] Phase 1 - Domain layer (spec 018)
- [ ] Phase 2 - External signals
- [ ] Phase 3 - Scoring + ML
- [ ] Phase 4 - LLM agents
- [ ] Phase 5 - ProcurementGraph + service
- [ ] Phase 6 - APEX app (spec 021)
- [ ] Phase 7 - Fixtures + rehearsal

## Reuse from existing platform

This module reuses:

- `backend.llm` - LLM adapter and circuit breaker
- `backend.integrations.oracle_apex` - APEX read-only ingestion and audited write-back
- `backend.predictions.agent_execution_repository` - audit trail of agent runs
- `backend.persistence` - Postgres connection and tenant scoping
- `backend.queue` and `backend.worker` - ARQ async dispatch

It does not modify or invoke `backend.predictions.graph.PredictionGraph` (the agronomic
crop-prediction pipeline). Both graphs coexist.
