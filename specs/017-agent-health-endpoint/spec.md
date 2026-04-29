# Feature Specification: Agent Health Endpoint and Live Dashboard Panel

**Feature Branch**: `017-agent-health-endpoint`
**Created**: 2026-04-28
**Status**: Draft
**Input**: Add a backend GET /api/v1/agents/health endpoint that reports real-time status for each LangGraph agent, and wire the frontend AgentHealthPanel to fetch live data instead of using hardcoded static state.

## Context

`frontend/src/components/AgentHealthPanel.tsx` initialises state with five hardcoded agent health objects. There is no `useEffect` fetching real data, and no backend endpoint for agent health exists. The panel never updates from real state. This spec covers: a backend endpoint that aggregates agent health from ARQ worker metrics (active jobs, recent error rates, last execution timestamps) and LangGraph checkpoint data, plus the frontend wiring to fetch and auto-refresh this data.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Backend exposes real agent health metrics (Priority: P1)

`GET /api/v1/agents/health` returns the current health status for each of the five pipeline agents (`data_analyst`, `ml_executor`, `recommendation_engine`, `explainability`, `reviewer`). For each agent, the response includes: status (`healthy`/`degraded`/`error`/`unknown`), last execution timestamp, P95 latency for the last 100 executions, error rate (errors / total in the last 15 minutes), and the current degradation flags active for that agent.

**Why this priority**: Without a real health endpoint, operators have no visibility into which agents are failing or slow. The hardcoded frontend panel gives false confidence.

**Independent Test**: Run five predictions to populate execution history. Call `GET /api/v1/agents/health?tenant_id=tenant-alpha`. Verify the response contains exactly five agent entries, each with a non-null `last_executed_at` timestamp and latency/error metrics derived from real execution records.

**Acceptance Scenarios**:

1. **Given** recent prediction executions exist in PostgreSQL, **When** `GET /api/v1/agents/health` is called, **Then** the response includes accurate execution counts, P95 latency, and error rates for each agent within the last 15 minutes.
2. **Given** an agent has not executed in the last 15 minutes, **When** the endpoint is called, **Then** that agent's status is `unknown` and metrics show zero executions.
3. **Given** an agent's error rate exceeds 10% in the last 15 minutes, **When** the endpoint is called, **Then** that agent's status is `degraded`.
4. **Given** an agent's error rate exceeds 50% in the last 15 minutes, **When** the endpoint is called, **Then** that agent's status is `error`.
5. **Given** a tenant with no execution history, **When** the endpoint is called, **Then** all agents return `status: "unknown"` with zero metrics - no cross-tenant data is returned.

---

### User Story 2 - Frontend AgentHealthPanel displays live data with auto-refresh (Priority: P1)

The `AgentHealthPanel` component fetches `GET /api/v1/agents/health` on mount and auto-refreshes every 30 seconds. While loading, it shows a skeleton state. Each agent card displays the real status badge (color-coded), last execution time (relative, e.g., "2 minutes ago"), P95 latency, and error rate. If a fetch fails, it shows the last known data with a "stale" indicator.

**Why this priority**: The panel is the primary observability surface for operators. Hardcoded data is actively misleading.

**Independent Test**: Mount `AgentHealthPanel` in a test environment with a mocked API handler returning known health data. Verify the component renders the five agents with the mocked values. Advance the mock timer by 31 seconds and verify a second fetch is triggered.

**Acceptance Scenarios**:

1. **Given** the health endpoint returns valid data, **When** `AgentHealthPanel` mounts, **Then** it renders five agent cards with status badges, latency, and error rate matching the API response.
2. **Given** the initial fetch succeeds and the component is visible for 31 seconds, **When** the auto-refresh timer fires, **Then** a second API call is made and the panel updates with new data.
3. **Given** a fetch fails (network error), **When** the panel renders, **Then** it shows the last successfully fetched data with a "data may be stale" indicator and does not crash.
4. **Given** an agent has `status: "error"`, **When** the panel renders, **Then** the agent card displays a visually distinct error state (not just a color change - accessible indicator required per WCAG 2.1 AA).
5. **Given** the component unmounts, **When** it remounts, **Then** no duplicate polling intervals are running.

---

### User Story 3 - Agent execution metadata is persisted per graph run (Priority: P2)

Every agent execution within a prediction run records its start time, end time, output state summary, and error (if any) to an `agent_executions` table. This data drives the health endpoint metrics and enables post-hoc debugging of individual agent failures within a specific prediction run.

**Why this priority**: Without per-execution records, the health endpoint has no data source. This is also required for the observability Tier 1 non-negotiable.

**Independent Test**: Run a prediction and query `SELECT agent_name, duration_ms, status FROM agent_executions WHERE prediction_id = '<id>'`. Verify five rows exist (one per agent), each with a non-null `duration_ms` and `status`.

**Acceptance Scenarios**:

1. **Given** a prediction completes successfully, **When** `agent_executions` is queried, **Then** five rows exist with `status: "success"` and positive `duration_ms`.
2. **Given** an agent fails mid-graph, **When** `agent_executions` is queried, **Then** the failed agent row has `status: "error"` and a non-null `error_message`, while upstream agents show `status: "success"`.
3. **Given** the graph is resumed from checkpoint, **When** `agent_executions` is queried, **Then** only the agents that re-executed after the checkpoint have new rows - resumed agents do not create duplicate rows.

---

### Edge Cases

- What happens when the health endpoint is called while a prediction is actively running (agent mid-execution)?
- How does the panel behave in air-gapped environments where the fetch may have high latency?
- What happens when `agent_executions` grows to millions of rows? (need index and retention policy)
- How does the WCAG-compliant status indicator work for users with screen readers?
- What happens when all five agents show `status: "unknown"` on a fresh deployment?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `GET /api/v1/agents/health` MUST return a JSON object with one entry per agent: `data_analyst`, `ml_executor`, `recommendation_engine`, `explainability`, `reviewer`.
- **FR-002**: Each agent entry MUST include: `status` (healthy/degraded/error/unknown), `last_executed_at` (ISO 8601 or null), `p95_latency_ms`, `error_rate_15m` (float 0-1), `total_executions_15m`, `active_degradation_flags`.
- **FR-003**: Status thresholds MUST be: `error_rate > 0.5` -> `error`, `error_rate > 0.1` -> `degraded`, `error_rate <= 0.1 and executions > 0` -> `healthy`, `executions == 0` -> `unknown`.
- **FR-004**: The endpoint MUST be scoped to the requesting tenant (no cross-tenant metrics).
- **FR-005**: Metrics MUST be derived from the `agent_executions` table, not from hard-coded values or Redis state.
- **FR-006**: An `agent_executions` table MUST be created in PostgreSQL with columns: `execution_id`, `prediction_id`, `tenant_id`, `agent_name`, `started_at`, `completed_at`, `duration_ms`, `status`, `error_message`, `degradation_flags`.
- **FR-007**: Every LangGraph node transition MUST write a row to `agent_executions` with timing data.
- **FR-008**: `agent_executions` MUST have a covering index on `(tenant_id, agent_name, started_at DESC)` for the 15-minute window query.
- **FR-009**: A data retention policy MUST delete `agent_executions` rows older than 90 days (configurable via `AGENT_EXECUTION_RETENTION_DAYS`).
- **FR-010**: `AgentHealthPanel` MUST replace all hardcoded state with a `useEffect` fetch to `GET /api/v1/agents/health?tenant_id={activeTenant}`.
- **FR-011**: `AgentHealthPanel` MUST poll every 30 seconds (configurable), cancel the interval on unmount, and not create duplicate intervals on re-render.
- **FR-012**: Status indicators MUST use both color and an explicit label/icon to satisfy WCAG 2.1 AA (no color-only state).
- **FR-013**: The panel MUST show a loading skeleton on initial fetch and a stale-data indicator when the last fetch failed.

### Key Entities

- **AgentHealthEntry**: API response object. Fields: `agent_name`, `status`, `last_executed_at`, `p95_latency_ms`, `error_rate_15m`, `total_executions_15m`, `active_degradation_flags`.
- **AgentExecution**: PostgreSQL row. Fields: `execution_id`, `prediction_id`, `tenant_id`, `agent_name`, `started_at`, `completed_at`, `duration_ms`, `status`, `error_message`, `degradation_flags`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `GET /api/v1/agents/health` responds in under 100 ms at P95 (single indexed query, no N+1).
- **SC-002**: `AgentHealthPanel` renders live data within 2 seconds of mount on a local network.
- **SC-003**: Zero hardcoded health values remain in `AgentHealthPanel.tsx` after implementation (verified by removing `sampleData.ts` import and confirming no TypeScript errors with the live data types).
- **SC-004**: WCAG 2.1 AA compliance verified: status badges use both color and text label; panel is keyboard-navigable; passes axe-core automated scan with zero violations.
- **SC-005**: 100% of completed prediction runs have exactly five `agent_executions` rows in PostgreSQL.
- **SC-006**: The 15-minute window query completes in under 50 ms for 1 million rows (verified with EXPLAIN ANALYZE on the covering index).
