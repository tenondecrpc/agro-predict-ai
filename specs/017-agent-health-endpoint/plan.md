# Implementation Plan: Agent Health Endpoint and Live Dashboard Panel

**Branch**: `017-agent-health-endpoint` | **Date**: 2026-04-29 | **Spec**: [spec.md](spec.md)

## Summary

Wire the existing agent health infrastructure together: inject PostgresAgentExecutionRepository into the app, persist agent execution records from LangGraph nodes to PostgreSQL, add data retention policy for agent_executions, and improve the frontend loading state from plain text to skeleton UI. The endpoint, migration, repository, and frontend component already exist but are not connected.

## Technical Context

**Language/Version**: Python 3.12, TypeScript
**Primary Dependencies**: FastAPI, PostgreSQL 16, React
**Storage**: PostgreSQL (agent_executions table)
**Testing**: pytest (backend), Vitest (frontend)
**Target Platform**: Linux server (Kubernetes) + Browser
**Project Type**: Web service (backend API + frontend dashboard)
**Performance Goals**: Health endpoint < 100ms P95, panel renders < 2s
**Constraints**: Tenant-scoped metrics, WCAG 2.1 AA, 90-day retention
**Scale/Scope**: 5 agents per tenant, 15-minute window queries

## Constitution Check

- **Agent-First Orchestration**: Execution tracking per agent node - no change to graph structure. PASS.
- **Data-Driven Decisions**: Health metrics derived from real execution data. PASS.
- **Test-First Validation**: Tests for persistence, endpoint accuracy, frontend rendering. PASS.
- **Observability & Explainability**: Per-agent execution records, P95 latency, error rates. PASS.
- **Resilience & Graceful Degradation**: Stale-data indicator on fetch failure. PASS.
- **WCAG 2.1 AA**: Color + text label for status, keyboard navigable. PASS.

## Project Structure

### Documentation (this feature)

```text
specs/017-agent-health-endpoint/
├── spec.md              # Feature specification
├── plan.md              # This file
└── tasks.md             # Task list
```

### Source Code (repository root)

```text
backend/src/backend/predictions/
├── health_api.py          # Existing: endpoint (no changes needed)
├── graph.py               # Modified: include tenant_id, started_at in exec records
├── service.py             # Modified: persist agent_executions after graph execution
├── agent_execution_repository.py  # Existing: PostgresAgentExecutionRepository
backend/src/backend/
├── app.py                 # Modified: wire PostgresAgentExecutionRepository to health router
├── compliance/
│   └── admin.py           # Modified: add agent_executions retention handler
backend/alembic/versions/
└── 20260430_0020_agent_executions.py  # Existing migration (no changes needed)
frontend/src/components/
└── AgentHealthPanel.tsx   # Modified: skeleton loading state, tenant context
frontend/src/types/
└── agent-health.ts        # Existing: type definitions (no changes needed)
backend/tests/
├── unit/
│   └── test_agent_health.py       # New: endpoint with wired repo tests
└── integration/
    └── test_agent_executions.py   # New: persistence from graph tests
```

## Complexity Tracking

No constitution violations. Health endpoint extends existing observability patterns.
