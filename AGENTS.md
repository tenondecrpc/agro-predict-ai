# AGENTS.md

Guidelines for agentic coding agents operating in this repository.

## Instruction Source

`AGENTS.md` is the single source of truth for repository instructions used by agent harnesses (Claude Code, Codex, OpenCode, and similar).

`.specify/memory/constitution.md` is the authoritative constitution for AgroPredict AI domain rules, design principles, and quality gates. It governs both the SpecKit feature development workflow and the runtime behavior of the deployed system.

`CLAUDE.md` is a thin bootstrap that defers to `AGENTS.md` and must not duplicate repository rules.

## Language

All agent communication and written outputs in this repository must be in English. This includes feature specs, design docs, task lists, code comments, commit messages, and PR descriptions.

## Formatting

These formatting rules apply to all agent-written output in this repository, including Codex, OpenCode, and Claude Code.

Use ASCII punctuation by default.

Do not use em dashes (`—`) or en dashes (`–`) in prose, bullet lists, headings, commit messages, plans, or code comments.

Always use the plain ASCII hyphen (`-`) instead.

Preferred example:

- `Planner artifact - feature spec and clarification notes`

## Project

AgroPredict AI is a multi-agent predictive intelligence system for agriculture and logistics that uses LangGraph to orchestrate specialized agents for data analysis, ML model execution, and actionable recommendations. It runs inside customer-owned Kubernetes with tenant and team isolation, horizontal scaling, auditability, and production-grade observability. There is no vendor-operated SaaS control plane and no cross-customer data plane. Connected and air-gapped deployment profiles are both first-class.

**Pipelines**:

- Prediction pipeline: Data ingestion -> FastAPI -> ARQ queue -> LangGraph graph (`data_analyst` -> `ml_executor` -> `recommendation_engine` -> `explainability` -> `reviewer`) -> actionable output
- Model pipeline: data validation -> feature engineering -> model training -> accuracy validation -> deployment with shadow-mode -> active runtime
- Config pipeline: admin UI or API -> versioned config in PostgreSQL -> shadow-mode validation -> active runtime graph

Runtime agents do not use Spec-Driven Development. They operate directly on validated data sources, execute models, and emit recommendations through the LangGraph state machine. SDD applies only to the development of new features for this application.

## Feature Development Workflow (SpecKit)

New features for this application follow the SpecKit workflow. This is the only SDD layer in this repository and it applies exclusively to human-driven feature development, not to runtime agent behavior.

**Lifecycle**: `constitution -> spec -> plan -> tasks -> implement -> test -> review -> deploy`

**Commands**:

- Create a new feature: `.specify/scripts/bash/create-new-feature.sh "feature description"` - creates a numbered branch under `specs/###-feature-name/` with a spec template
- Plan a feature: `.specify/scripts/bash/setup-plan.sh` - generates the implementation plan from the spec
- Update agent context: `.specify/scripts/bash/update-agent-context.sh` - refreshes agent context files

**Artifact structure** (per feature under `specs/###-feature-name/`):

- `spec.md` - Feature specification with user stories, acceptance criteria, and requirements
- `plan.md` - Implementation plan with technical context, architecture decisions, and project structure
- `tasks.md` - Ordered, testable task list organized by user story
- `research.md` - Phase 0 research output
- `data-model.md` - Data model and entity definitions
- `contracts/` - API contract definitions

**Workflow rules**:

- Every feature starts with a spec that defines user stories, requirements, and success criteria
- The plan must pass a Constitution Check against `.specify/memory/constitution.md` before implementation begins
- Tasks are organized by user story so each story can be implemented, tested, and delivered independently
- Tests are written before implementation (TDD) for all agents, models, and integrations
- No feature merges without passing the verification gates defined below

## Repository Status

This repository is in early implementation. Executable backend and frontend slices now exist under `backend/` and `frontend/`. Human-readable operator and status documentation now exists under `docs/`, machine-readable contracts live under `contracts/`, deployable operational artifacts live under `operations/`, and `helm/` remains a scaffold.

Scaffold targets remain:

- `backend/` - FastAPI app, ARQ workers, LangGraph graph, ML adapters, Oracle APEX integration
- `frontend/` - Vite + React + TypeScript monitoring dashboards and admin UI
- `helm/` - Helm charts for Kubernetes deployment (connected and `air_gapped` profiles)
- `contracts/` - Machine-readable API contracts and model validation registries
- `operations/` - Deployable operational artifacts such as alert rules and dashboards
- `docs/` - Human-readable operator, integrator, and developer documentation

Use `uv` for Python dependency management, environment synchronization, and Python command execution.

Current backend commands from the repository root:

- Sync dependencies: `uv sync --project backend --dev`
- Lint: `uv run --project backend ruff check backend/src backend/tests`
- Test: `uv run --project backend pytest`

Current frontend commands from the repository root:

- Install dependencies: `npm install --prefix frontend`
- Test: `npm run --prefix frontend test -- --run`
- Build: `npm run --prefix frontend build`

## Deployment Model

- Self-hosted only inside customer-owned infrastructure.
- No vendor-operated SaaS control plane.
- No cross-customer data plane. "Multi-tenancy" only means teams, business units, and projects inside one customer-owned deployment.
- Customer-owned secrets, data stores, object storage, and ML provider accounts are mandatory.
- Air-gapped deployment is a first-class supported profile.

## Core Architecture

- LangGraph orchestrates `data_analyst`, `ml_executor`, `recommendation_engine`, `explainability`, and `reviewer` roles.
- FastAPI handles APIs, webhooks, and admin interfaces.
- ARQ and Redis handle queueing, caching, and circuit breaker state.
- PostgreSQL is the durable system of record for predictions, model metadata, audit logs, and configuration.
- Vite + React + TypeScript power the monitoring dashboards and admin UI.
- Oracle APEX adapter provides enterprise data synchronization (read-only ingestion, audited write-back).
- scikit-learn provides ML models with an extensible adapter pattern for deep learning frameworks.
- Optional internal knowledge retrieval uses `pgvector` in PostgreSQL, not a separate datastore.

## Core Stack

- Orchestration: LangGraph `StateGraph`, `langgraph-checkpoint-postgres`, `langgraph.store.postgres`
- API and workers: FastAPI, ARQ
- ML: scikit-learn (extensible adapter for deep learning frameworks)
- Python packaging and environments: `uv`
- Persistence and queues: PostgreSQL 16, Redis 7, optional `pgvector`
- Frontend: Vite, React, TypeScript
- Integration: Oracle APEX adapter
- Deployment: Helm, Kubernetes (connected and `air_gapped` profiles)
- Observability: OpenTelemetry, Prometheus, Grafana, Loki
- Delivery and control: Helm, Kustomize, Argo Rollouts, OpenFeature with Unleash or LaunchDarkly
- Security and supply chain: `gitleaks`, `trufflehog`, `syft`, `cosign`, Trivy, Grype, OSV-Scanner

## Execution Model

- Runtime agents execute the prediction pipeline directly: data validation -> feature engineering -> model execution -> recommendation generation -> explainability -> review.
- No SDD artifact chain exists at runtime. Agents operate on validated data, model outputs, and tenant configuration.
- Human approval is break-glass only for exception paths such as security review, model accuracy regression, data source contradictions, budget exhaustion, policy violations, or unresolved data ambiguity.
- Feature development for this application follows the SpecKit workflow defined above.

## Design Principles

- **Agent-First Orchestration**: Every capability is orchestrated through LangGraph StateGraph agents. Agents are specialized, independently testable, and communicate through typed state transitions. No monolithic control flow - all logic flows through the agent graph. Each agent has a single responsibility, explicit input/output contracts, and deterministic fallback behavior when upstream agents fail.
- **Data-Driven Decisions (NON-NEGOTIABLE)**: All recommendations, predictions, and alerts MUST be grounded in verifiable data sources. Models must expose confidence intervals, feature importance, and data freshness metadata. No recommendation is emitted without an attached data provenance chain. When data is stale, incomplete, or contradictory, the system MUST flag uncertainty rather than fabricate outputs.
- **Test-First Validation (NON-NEGOTIABLE)**: Every agent, model, and integration point requires tests before implementation. TDD is mandatory: tests written -> tests fail -> implementation -> tests pass. Model tests include regression checks against known datasets, drift detection thresholds, and edge-case scenarios (extreme weather, missing sensor data, outlier logistics events). Integration tests verify agent communication contracts and state transitions.
- **Observability & Explainability**: Every agent execution emits structured logs, metrics, and traces. Predictions include explanation artifacts: which features drove the output, what data was used, and what confidence level applies. The system MUST support post-hoc analysis of any recommendation. Dashboards expose agent health, model accuracy trends, data pipeline latency, and prediction drift.
- **Resilience & Graceful Degradation**: The system MUST operate under partial failure conditions. When an agent fails, downstream agents receive explicit failure signals and degrade gracefully rather than crash. Data pipeline interruptions trigger cached-model fallback with staleness warnings. External API failures (weather services, satellite imagery, market data) route to backup providers or historical baselines. Air-gapped deployments MUST function without external connectivity using local model caches and stored datasets.

## Tier 1 Non-Negotiables

- All predictions MUST be grounded in verifiable data sources with complete provenance chains.
- Every agent emits structured logs, metrics, and traces; predictions include explanation artifacts.
- Test-first development is mandatory for all agents, models, and integrations; no merge without passing unit and contract tests.
- System operates under partial failure with graceful degradation; cached-model fallback with staleness warnings on data pipeline interruption.
- Agent communication ONLY through LangGraph state - no direct inter-agent API calls.
- Model artifacts are versioned with metadata (training date, dataset hash, accuracy metrics).
- External integrations use adapter interfaces with circuit breaker protection.
- Oracle APEX integration is read-only for data ingestion; write-back is explicit and audited.
- Frontend consumes data through API layer only - no direct database access.
- Both connected and `air_gapped` deployment profiles are mandatory.
- Comprehensive testing is mandatory: unit, integration, E2E, chaos, and model regression.
- Observability is mandatory: structured logs, metrics, traces, health probes, dashboards, and alerting.
- Public API versioning and diff gates are mandatory.
- Dead letter queue support is mandatory.
- Graceful shutdown to checkpoint boundaries is mandatory.
- Configuration must be stored in PostgreSQL with versioning, audit trail, rollback, and shadow-mode validation.
- Schema changes must use expand/contract migration discipline with reversibility tests.
- Feature-flag kill switches are mandatory for high-risk runtime capabilities.
- Kubernetes-native deployment is mandatory: Helm, HPA, health probes, and resource quotas are required.
- Multi-tenancy is mandatory with tenant and team isolation across credentials, data, models, budgets, and queue behavior.
- Credential rotation SLA and dual-control break-glass are mandatory.
- Data retention, deletion, and DPA acknowledgement are mandatory.
- Disaster recovery is mandatory with backups, restore drills, and defined RPO and RTO.
- Progressive delivery with automated rollback is mandatory.
- Rate limiting and weighted-fair queueing are mandatory.
- SLOs, burn-rate alerting, and error-budget policy are mandatory.
- Public status communication and incident runbooks are mandatory.

## Tier 2 Goals With Allowed Degradation

- Visual agent graph editor aims for full node, edge, route, and interrupt CRUD; acceptable degradation is read-only visualization plus JSON config import and export.
- Internationalization aims for full Spanish locale; acceptable degradation is English-only with extraction infrastructure ready.
- WCAG 2.1 AA end-to-end is the target; the non-negotiable subset is no color-only state, keyboard reachability of all interactive elements, `prefers-reduced-motion` support, and AA contrast on all text.
- Deep learning framework support aims for extensible adapter with multiple backends; acceptable degradation is scikit-learn only at GA with adapter interface ready.
- Real-time sensor data streaming aims for full event-driven ingestion; acceptable degradation is batch polling with streaming infrastructure ready.
- Optional internal RAG via `pgvector` may stay disabled at GA; if enabled it must remain tenant-scoped, read-only during prediction execution, and reuse PostgreSQL.

## Protected Workflow Invariants

- All predictions must originate from validated data sources with passing data quality gates.
- No model may emit recommendations without passing data quality gates and accuracy validation.
- Any path to production recommendations must traverse model execution, explainability verification, and review approval.
- Every failure terminal path must map to an explicit escalation reason and a registered escalation sink.
- Human approval is allowed only as break-glass control on exception paths; the normal success path cannot require manual approval.

## Guardrails

- Do not propose or implement vendor-hosted control planes or any cross-customer data plane.
- Do not introduce a new production datastore for predictions, model metadata, config, audit, or optional internal knowledge retrieval. Extend PostgreSQL (with `pgvector` when RAG is enabled) instead.
- Do not allow any prediction path to run before data quality gates pass and readiness is confirmed.
- Do not route the normal success path through human approval. Interrupts are break-glass only.
- Do not bypass the mandatory chain on any path that can reach production recommendations: model execution -> tests -> explainability verification -> review approval.
- Do not weaken Tier 1 non-negotiables. A proposal that weakens a Tier 1 rule is invalid unless it is explicitly framed as amending `.specify/memory/constitution.md` itself.
- Oracle APEX integration must remain read-only unless explicit audited write-back is approved.
- Do not store credentials in application config, environment variables committed to Git, frontend bundles, or logs. All secrets flow through Vault or External Secrets Operator with envelope encryption.
- Do not special-case the air-gapped profile after the fact. Every feature must reason about connected and `air_gapped` deployment from the design stage.
- Treat changes to Helm values, network policies, RBAC, DB migrations, feature-flag kill switches, and graph escalation sinks as high-risk and call them out explicitly.
- Avoid designs that grant any agent more privilege than its role boundary requires.

## SpecKit Feature Artifact Rules

When drafting feature artifacts under `specs/`, follow the rules for the artifact type being produced.

### Spec

- Include explicit user stories with priorities, acceptance criteria, edge cases, and non-goals.
- Preserve self-hosted-only deployment, customer-owned data and secrets, and single-customer infrastructure boundaries.
- Preserve tenant and team isolation, least-privilege tool governance, data-driven decision requirements, and PostgreSQL-backed config and state.
- If prediction behavior is in scope, state the data quality gate explicitly: no prediction before data sources are validated and readiness is confirmed.
- If UI is in scope, include accessibility requirements for keyboard reachability, no color-only state, `prefers-reduced-motion`, and AA text contrast.
- If graph or runtime behavior is in scope, preserve config-driven graph invariants, mandatory review, and explicit escalation paths.
- If security or operations are in scope, include observability, rollback, auditability, and failure-mode requirements directly in the spec.
- If model behavior is in scope, include accuracy regression requirements, data provenance chains, and explainability verification criteria.

### Plan

- Reuse and extend the architecture described in the constitution instead of inventing parallel systems.
- Keep configuration versioned, auditable, rollbackable, and compatible with PostgreSQL-backed config plus shadow mode.
- Preserve protected workflow invariants: data quality gate before prediction, mandatory test and review before recommendation release, and a registered escalation sink on failure paths.
- Document enforcement points, failure modes, observability, and rollback for security-sensitive or tenant-boundary changes.
- Optional capabilities must remain feature-flagged, tenant-scoped, and disabled by default unless the constitution says otherwise.
- Do not introduce a new production datastore for optional internal knowledge retrieval; use PostgreSQL plus `pgvector` when that capability is enabled.
- Avoid designs that grant any agent more privilege than its role boundary requires.
- The plan must pass a Constitution Check against `.specify/memory/constitution.md` before tasks are generated.

### Tasks

- Break work into small, ordered, testable tasks with explicit verification steps.
- Organize tasks by user story so each story can be implemented, tested, and delivered independently.
- Put spec and plan refinement before implementation, and implementation before tests, review, and release actions.
- Include tests, observability, security or policy validation, and docs or config updates whenever applicable.
- If a Tier 2 capability ships in degraded form, include a follow-up parity task tied to the allowed degradation path in the constitution.
- Do not schedule prediction implementation tasks before the relevant spec, plan, and task artifacts are complete.

## Workflow

- **Create feature**: Run `.specify/scripts/bash/create-new-feature.sh "description"` to create a feature branch and spec template under `specs/`.
- **Plan**: Fill in `spec.md` with user stories, requirements, and acceptance criteria. Then run `.specify/scripts/bash/setup-plan.sh` to generate `plan.md`.
- **Constitution Check**: Verify the plan against `.specify/memory/constitution.md` before generating tasks.
- **Tasks**: Generate `tasks.md` organized by user story with test-first ordering.
- **Implement**: Work through tasks in order. Tests before implementation. Core before integration.
- **Review**: All changes require peer review. Verify Tier 1 non-negotiables are preserved.
- **Deploy**: Use Helm for Kubernetes deployment. Feature-flag high-risk capabilities. Progressive delivery with rollback.

## Verification

- For backend changes, install and synchronize Python dependencies with `uv`, then run the relevant backend verification via `uv run`; at minimum use `uv run --project backend ruff check backend/src backend/tests` and `uv run --project backend pytest`, then confirm graph paths still traverse test, explainability verification, review, and pre-release sync before recommendation release.
- For model changes, run accuracy regression tests against held-out datasets and verify data provenance chain integrity.
- For data pipeline changes, run data validation tests and verify Oracle APEX consistency checks.
- For frontend changes, confirm the accessibility non-negotiable subset: no color-only state, keyboard reachability of every interactive element, `prefers-reduced-motion` support, and AA text contrast.
- For Helm, Kustomize, RBAC, or network policy changes, include manual verification notes and dry-run or shadow-mode output; flag as high-risk.
- For schema changes, verify expand/contract migration discipline with reversibility tests.
- For tenant-boundary, secret-handling, or webhook changes, include observability, audit, and failure-mode notes directly in the PR description.
- UI changes should include screenshots or a short note describing what was manually verified.
- Feature specs and plans must pass Constitution Check against `.specify/memory/constitution.md` before implementation begins.

## References

- AgroPredict AI Constitution: `.specify/memory/constitution.md`
- SpecKit templates: `.specify/templates/`
- SpecKit scripts: `.specify/scripts/bash/`
- Claude Code bootstrap: `CLAUDE.md`
- Feature specs: `specs/`
