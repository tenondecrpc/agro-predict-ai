# Implementation Plan: Prediction Pipeline

**Branch**: `001-prediction-pipeline` | **Date**: 2026-04-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-prediction-pipeline/spec.md`

## Summary

Build a new LangGraph-based prediction pipeline that orchestrates five specialized agricultural agents (`data_analyst`, `ml_executor`, `recommendation_engine`, `explainability`, `reviewer`) to generate crop and logistics predictions with confidence intervals, feature importance, and explainability artifacts. The pipeline operates alongside the existing SpecKit runtime workflow and exposes `POST /api/v1/predictions` for synchronous requests and ARQ enqueueing for async processing.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: FastAPI, LangGraph, ARQ, scikit-learn, SQLAlchemy (async), pydantic  
**Storage**: PostgreSQL for prediction results, agent execution metadata, explanation artifacts; Redis for ARQ queue and circuit breaker state  
**Testing**: pytest with async support, httpx for API tests  
**Target Platform**: Linux server (containerized), both connected and air-gapped Kubernetes profiles  
**Project Type**: Web service - backend API  
**Performance Goals**: P95 latency < 30s for standard inputs, cached-model fallback < 5s  
**Constraints**: No external API calls in air-gapped; all predictions require passing data quality gates before model execution  
**Scale/Scope**: Multi-tenant with tenant/team isolation

## Constitution Check

| Principle | Check | Notes |
|-----------|-------|-------|
| I. Agent-First Orchestration | PASS | Five specialized agents with single responsibilities, typed state transitions, deterministic fallback |
| II. Data-Driven Decisions | PASS | Provenance chains mandatory, uncertainty flagging instead of fabrication, confidence intervals required |
| III. Test-First Validation | PASS | TDD enforced: tests first, then implementation. Unit + integration + contract tests |
| IV. Observability & Explainability | PASS | Every agent emits telemetry; predictions include explanation artifacts |
| V. Resilience & Graceful Degradation | PASS | Cached-model fallback, explicit failure signals to downstream agents, graceful degradation on timeout |

## Project Structure

### Documentation (this feature)

```text
specs/001-prediction-pipeline/
├── plan.md              # This file
├── tasks.md             # Implementation tasks
├── contracts/           # API contracts
│   └── prediction.yaml
└── data-model.md        # Entity definitions
```

### Source Code (repository root)

```text
backend/src/backend/
├── app.py                    # Add prediction router
├── predictions/              # NEW: prediction pipeline module
│   ├── __init__.py
│   ├── models.py             # Prediction, AgentExecution, ExplanationArtifact entities
│   ├── graph.py              # LangGraph StateGraph orchestration
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── data_analyst.py
│   │   ├── ml_executor.py
│   │   ├── recommendation_engine.py
│   │   ├── explainability.py
│   │   └── reviewer.py
│   ├── repository.py         # PredictionRepository protocol + Postgres impl
│   ├── service.py            # PredictionService (enqueue + execute)
│   ├── api.py                # FastAPI router for /api/v1/predictions
│   └── telemetry.py          # Prediction pipeline telemetry
└── persistence/
    └── factory.py            # Add prediction_repository to PersistenceAdapters
```

```text
backend/tests/
├── unit/predictions/         # NEW: unit tests per agent
│   ├── test_data_analyst.py
│   ├── test_ml_executor.py
│   ├── test_recommendation_engine.py
│   ├── test_explainability.py
│   └── test_reviewer.py
├── integration/
│   └── test_predictions_api.py
└── contracts/
    └── test_prediction_contracts.py
```

## Architecture Decisions

1. **New module, not replacement**: The prediction pipeline lives in `backend.predictions` alongside the existing `backend.runtime`. Both share `PersistenceAdapters` but have separate LangGraph graphs.

2. **Typed state dict**: The prediction graph uses `PredictionState(TypedDict)` with explicit fields for input, intermediate outputs, and final result.

3. **Repository pattern**: `PredictionRepository` abstracts persistence, with `PostgresPredictionRepository` and `InMemoryPredictionRepository` implementations.

4. **Agent communication via LangGraph state only**: No direct inter-agent API calls, satisfying FR-011.

5. **Cached-model fallback**: The `ml_executor` agent checks a local model cache (file system or object storage adapter) before failing.

6. **Timeout enforcement**: The prediction pipeline uses `langgraph` timeout configuration with a configurable default of 30 seconds.

## Complexity Tracking

> No Constitution violations. All principles satisfied.

## Failure Modes & Rollback

- **Schema changes**: Add `predictions`, `agent_executions`, `explanation_artifacts` tables via Alembic migration with rollback tested.
- **Feature flag**: Wrap the prediction router behind a feature flag (`predictions_api_enabled`) to allow kill-switch.
- **Graph changes**: New graph is additive; existing `RuntimeWorkflow` is untouched.

## Verification Gates

1. `uv run --project backend ruff check backend/src backend/tests`
2. `uv run --project backend pytest backend/tests/unit/predictions/`
3. `uv run --project backend pytest backend/tests/integration/test_predictions_api.py`
4. `uv run --project backend pytest backend/tests/contracts/test_prediction_contracts.py`
