<!--
Sync Impact Report:
- Version change: N/A (first concrete version) -> 1.0.0
- Modified principles: All 5 principles instantiated from template placeholders
- Added sections: "Technology Stack & Architecture", "Development Workflow & Quality Gates"
- Removed sections: None
- Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ compatible (Constitution Check references generic gates)
  - .specify/templates/spec-template.md: ✅ compatible (no constitution-specific constraints)
  - .specify/templates/tasks-template.md: ✅ compatible (task structure aligns with principles)
  - .specify/templates/commands/*.md: ⚠ no command files exist yet (pending)
- Follow-up TODOs:
  - TODO(RATIFICATION_DATE): Original adoption date unknown; set to 2026-04-28 as first concrete version
-->

# AgroPredict AI Constitution

## Core Principles

### I. Agent-First Orchestration

Every capability is orchestrated through LangGraph StateGraph agents. Agents are specialized, independently testable, and communicate through typed state transitions. No monolithic control flow - all logic flows through the agent graph. Each agent has a single responsibility, explicit input/output contracts, and deterministic fallback behavior when upstream agents fail.

Rationale: Multi-agent decomposition enables parallel reasoning, graceful degradation, and targeted model selection per task. Agriculture and logistics domains require distinct expertise (weather modeling, crop prediction, route optimization) that maps naturally to specialized agents.

### II. Data-Driven Decisions (NON-NEGOTIABLE)

All recommendations, predictions, and alerts MUST be grounded in verifiable data sources. Models must expose confidence intervals, feature importance, and data freshness metadata. No recommendation is emitted without an attached data provenance chain. When data is stale, incomplete, or contradictory, the system MUST flag uncertainty rather than fabricate outputs.

Rationale: Agricultural and logistics decisions carry real economic and environmental risk. Hallucinated or ungrounded predictions can cause crop loss, supply chain disruption, or financial harm. Data provenance is a safety requirement, not a nice-to-have.

### III. Test-First Validation (NON-NEGOTIABLE)

Every agent, model, and integration point requires tests before implementation. TDD is mandatory: tests written -> tests fail -> implementation -> tests pass. Model tests include regression checks against known datasets, drift detection thresholds, and edge-case scenarios (extreme weather, missing sensor data, outlier logistics events). Integration tests verify agent communication contracts and state transitions.

Rationale: ML systems degrade silently. Without rigorous test discipline, model drift, data schema changes, and agent contract violations go undetected until production impact occurs.

### IV. Observability & Explainability

Every agent execution emits structured logs, metrics, and traces. Predictions include explanation artifacts: which features drove the output, what data was used, and what confidence level applies. The system MUST support post-hoc analysis of any recommendation. Dashboards expose agent health, model accuracy trends, data pipeline latency, and prediction drift.

Rationale: Operators and agronomists must trust and audit system outputs. Explainability is required for regulatory compliance, user trust, and continuous model improvement. Black-box predictions are unacceptable in production agriculture.

### V. Resilience & Graceful Degradation

The system MUST operate under partial failure conditions. When an agent fails, downstream agents receive explicit failure signals and degrade gracefully rather than crash. Data pipeline interruptions trigger cached-model fallback with staleness warnings. External API failures (weather services, satellite imagery, market data) route to backup providers or historical baselines. Air-gapped deployments MUST function without external connectivity using local model caches and stored datasets.

Rationale: Agricultural operations run in remote areas with unreliable connectivity. Logistics systems face network partitions and third-party outages. The system must remain useful, not silently fail, when components degrade.

## Technology Stack & Architecture

The system is built on the following technology foundation:

- **Orchestration**: LangGraph StateGraph for agent coordination and state management
- **API Layer**: FastAPI for REST endpoints, webhooks, and admin interfaces
- **ML Stack**: scikit-learn for classical models, with extensible adapter pattern for deep learning frameworks
- **Persistence**: PostgreSQL for structured data, model metadata, audit logs, and configuration
- **Frontend**: React for monitoring dashboards, admin panels, and user-facing recommendation interfaces
- **Integration**: Oracle APEX for enterprise data synchronization and legacy system bridging
- **Queue & Cache**: Redis for agent task queuing, result caching, and circuit breaker state
- **Deployment**: Docker containers with Kubernetes orchestration for connected and air-gapped profiles

Architecture constraints:

- Agents communicate ONLY through LangGraph state - no direct inter-agent API calls
- Model artifacts are versioned and stored with metadata (training date, dataset hash, accuracy metrics)
- All external integrations use adapter interfaces with circuit breaker protection
- Oracle APEX integration is read-only for data ingestion; write-back is explicit and audited
- Frontend consumes data through API layer only - no direct database access

## Development Workflow & Quality Gates

All feature development follows this workflow:

1. **Specification**: Feature spec with user stories, acceptance criteria, and data requirements
2. **Clarification**: Ambiguity resolution with domain experts (agronomists, logistics planners)
3. **Design**: Agent graph changes, model selection rationale, data pipeline modifications
4. **Implementation**: Test-first development with contract tests for agent interfaces
5. **Validation**: Model accuracy checks, integration tests, explainability verification
6. **Review**: Peer review of agent logic, model choices, and data handling
7. **Release**: Staged rollout with feature flags and rollback capability

Quality gates:

- No agent merges without passing unit tests and contract tests
- Model changes require accuracy regression tests against held-out datasets
- Data schema changes require migration scripts with rollback paths
- Frontend changes require accessibility compliance (WCAG 2.1 AA subset)
- Oracle APEX integration changes require data consistency verification

## Governance

This constitution supersedes all other development practices within the AgroPredict AI project. Amendments require:

1. A documented proposal stating the change, rationale, and impact analysis
2. Review by at least two project maintainers
3. Migration plan for any breaking changes to agent contracts or data schemas
4. Update to this document with version increment and amendment date

Versioning policy follows semantic versioning:

- **MAJOR**: Backward-incompatible changes to agent contracts, data schemas, or principle removals
- **MINOR**: New agents, new model types, new integrations, or principle additions
- **PATCH**: Bug fixes, clarifications, wording improvements, non-semantic refinements

All pull requests MUST verify compliance with these principles during review. Complexity introduced by new agents or models must be justified with documented tradeoff analysis. Development guidance for runtime agent behavior is maintained in the project documentation under `docs/`.

**Version**: 1.0.0 | **Ratified**: 2026-04-28 | **Last Amended**: 2026-04-28
