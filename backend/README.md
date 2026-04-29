# AgroPredict AI Backend

This directory contains the first executable backend slice for AgroPredict AI.

## Commands

- Sync dependencies: `uv sync --project backend --dev`
- Development sync installs the FastAPI CLI requirements needed by `uv run --project backend fastapi dev backend/src/backend/app.py`
- Run tests: `uv run --project backend pytest`
- Run lint: `uv run --project backend ruff check backend/src backend/tests`

## Current scope

The current implementation covers these backend slices:

- prediction pipeline with data analysis, model execution, recommendation generation, explainability, review, and tenant-scoped persistence
- platform contracts for API surface inventory, weighted worker dispatch, drain handling, DLQ capture, and sandbox template generation
- security policy primitives for OIDC-style claim mapping, RBAC, webhook verification, prompt safety, and repository guardrails
- LLM governance primitives for model catalog validation, provider failover, atomic budget reservations, and metering rollups and exports
- control-plane primitives for graph validation, agent configuration governance, shadow-mode evidence, and versioned activation with rollback-safe snapshot pinning
- operations primitives for observability, SLO evaluation, release gates, resilience planning, retention, and quality-policy enforcement
