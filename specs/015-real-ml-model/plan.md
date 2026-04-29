# Implementation Plan: Real ML Model with Adapter Pattern

**Branch**: `015-real-ml-model` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)

## Summary

Complete the real ML model implementation by adding shadow-mode dual execution at runtime, a PostgreSQL-backed model repository (replacing InMemory), and wiring the model registry into the startup selection and promotion flow. The core model loading, training script, OOD detection, and formula fallback are already implemented.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: scikit-learn, joblib, FastAPI, SQLAlchemy, PostgreSQL 16
**Storage**: PostgreSQL (model_registry, shadow_comparisons), filesystem (.joblib artifacts)
**Testing**: pytest
**Target Platform**: Linux server (Kubernetes)
**Project Type**: Web service (backend API + workers)
**Performance Goals**: Model loading < 2s for artifacts up to 500MB
**Constraints**: Versioned artifacts, shadow-mode without affecting caller response
**Scale/Scope**: Multiple model versions per crop, active + shadow concurrent

## Constitution Check

- **Agent-First Orchestration**: ml_executor agent uses adapter interface - no change to graph structure. PASS.
- **Data-Driven Decisions**: Real model predictions with confidence intervals and feature importance. PASS.
- **Test-First Validation**: Tests for shadow-mode, PG repo, model loading, OOD detection. PASS.
- **Observability & Explainability**: Shadow comparisons persisted for post-hoc analysis. PASS.
- **Resilience & Graceful Degradation**: Formula fallback when model missing. PASS.
- **Model versioning**: Registry with metadata, promote/archive workflow. PASS.

## Project Structure

### Documentation (this feature)

```text
specs/015-real-ml-model/
├── spec.md              # Feature specification
├── plan.md              # This file
└── tasks.md             # Task list
```

### Source Code (repository root)

```text
backend/src/backend/predictions/
├── models/
│   └── ml_models/
│       ├── repository.py        # Modified: add PostgresModelRepository
│       └── schema.py            # Modified: add model_registry Table definition
backend/src/backend/ml/
├── adapter.py                   # Existing: ScikitLearnAdapter, FormulaFallbackAdapter
├── control_plane/
│   ├── shadow.py                # Existing: ShadowModeEvaluator
│   └── service.py               # Modified: wire shadow dual-execution, can_promote
├── shadow_comparisons/
│   └── repository.py            # New: ShadowComparisonRepository
backend/src/backend/predictions/agents/
└── ml_executor.py               # Modified: support shadow-mode dual execution
backend/alembic/versions/
└── 20260430_0019_model_registry.py  # Existing migration (no changes needed)
backend/tests/
├── unit/
│   └── test_shadow_mode.py      # New: shadow dual-execution tests
└── integration/
    └── test_model_repo.py       # New: PostgreSQL model repo tests
```

## Complexity Tracking

No constitution violations. Shadow-mode adds complexity but is required by spec and constitution.
