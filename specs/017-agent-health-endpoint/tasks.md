# Tasks: Agent Health Endpoint and Live Dashboard Panel

**Input**: Design documents from `specs/017-agent-health-endpoint/`
**Prerequisites**: spec.md ✅, plan.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Verify `agent_executions` migration exists and is applied
- [ ] T002 [P] Verify `agent_executions` table has the covering index `ix_agent_exec_tenant_agent_started`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire the existing infrastructure together

- [ ] T003 Wire `PostgresAgentExecutionRepository` into the health router in `backend/src/backend/app.py` - instantiate it and pass to `build_agent_health_router()`
- [ ] T004 [P] Add `tenant_id` and `started_at` fields to `_make_exec_record()` in `backend/src/backend/predictions/graph.py`

**Checkpoint**: Health endpoint infrastructure connected, exec records have complete data

---

## Phase 3: User Story 1 - Backend exposes real agent health metrics (Priority: P1)

**Goal**: GET /api/v1/agents/health returns real metrics from agent_executions table

### Tests for User Story 1

- [ ] T005 [P] [US1] Add test verifying health endpoint returns 5 agents with non-null metrics when repo is wired in `backend/tests/unit/test_agent_health.py`

### Implementation for User Story 1

- [ ] T006 [US1] In `backend/src/backend/predictions/health_api.py`, ensure default behavior when `repository=None` returns 503 with clear message instead of all-unknown data
- [ ] T007 [US1] Verify status thresholds (FR-003) produce correct status values for each error rate range in `backend/src/backend/predictions/agent_execution_repository.py`

**Checkpoint**: Health endpoint returns real data when wired, 503 when not wired

---

## Phase 4: User Story 3 - Agent execution metadata persisted per graph run (Priority: P2)

**Goal**: Every LangGraph node writes execution records to PostgreSQL

### Tests for User Story 3

- [ ] T008 [P] [US3] Add integration test verifying 5 agent_executions rows exist after a completed prediction in `backend/tests/integration/test_agent_executions.py`

### Implementation for User Story 3

- [ ] T009 [US3] After graph execution in `backend/src/backend/predictions/service.py`, extract `agent_executions_raw` from graph state and persist each record to PostgreSQL via `PostgresAgentExecutionRepository`
- [ ] T010 [US3] In `backend/src/backend/predictions/graph.py`, add `tenant_id` parameter to `PredictionGraph.execute()` and pass it through to each node so execution records include tenant scope

**Checkpoint**: All 5 agent execution rows persisted per prediction run

---

## Phase 5: User Story 2 - Frontend AgentHealthPanel displays live data (Priority: P1)

**Goal**: Panel fetches real API data, auto-refreshes, shows skeleton loading state

### Implementation for User Story 2

- [ ] T011 [P] [US2] Replace hardcoded `tenant-alpha` with active tenant context prop in `frontend/src/components/AgentHealthPanel.tsx`
- [ ] T012 [US2] Replace plain "Loading agent health data..." text with a skeleton loading component in `frontend/src/components/AgentHealthPanel.tsx`
- [ ] T013 [US2] Verify WCAG 2.1 AA compliance: `aria-label` on status badges, keyboard navigation, color-contrast on error/degraded states in `frontend/src/components/AgentHealthPanel.tsx`

**Checkpoint**: Panel renders live data with skeleton loading, WCAG compliant

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T014 Add `agent_executions` retention policy handler to delete records older than `AGENT_EXECUTION_RETENTION_DAYS` (default 90) in `backend/src/backend/compliance/admin.py`
- [ ] T015 [P] Add `AGENT_EXECUTION_RETENTION_DAYS` env var configuration in `backend/src/backend/core/config.py`
- [ ] T016 Run all backend tests: `uv run --project backend pytest`
- [ ] T017 Run backend lint: `uv run --project backend ruff check backend/src backend/tests`
- [ ] T018 Frontend build: `npm run --prefix frontend build`

---

## Dependencies & Execution Order

- **Phase 1 (T001-T002)**: Can start immediately
- **Phase 2 (T003-T004)**: Depends on Phase 1 - **CRITICAL** - unblocks all US
- **US1 (T005-T007)**: Depends on Phase 2
- **US3 (T008-T010)**: Depends on Phase 2 - needed for US1 data
- **US2 (T011-T013)**: Depends on US1 (needs live API)
- **Polish (T014-T018)**: Depends on all US complete

### Parallel Opportunities

- T005, T008 can run in parallel (different test files)
- T011 can run in parallel with US1 implementation
- T015 can run in parallel with T014
