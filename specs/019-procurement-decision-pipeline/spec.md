# Feature Specification: Procurement Decision Pipeline

**Feature Branch**: `019-procurement-decision-pipeline`
**Created**: 2026-04-29
**Status**: Draft
**Input**: Adapt the LangGraph StateGraph (`013-langgraph-stategraph-llm`) to power an Intelligent Purchasing Copilot. Given a purchase request and validated quotations from `018-procurement-domain`, the pipeline must summarize each offer, compare them, and emit a justified recommendation that selects the best alternative.

## Context

The existing prediction pipeline runs five LangGraph agents (`data_analyst`, `ml_executor`, `recommendation_engine`, `explainability`, `reviewer`) over a typed `PredictionState`. This feature extends that pipeline to a procurement-specific graph that consumes `PurchaseRequest` and validated `Quotation` records and produces a `RecommendedOffer` with justification.

Reused infrastructure:

- LangGraph StateGraph with `langgraph-checkpoint-postgres` (from `013-langgraph-stategraph-llm`).
- LLM adapter, secure credential handling, circuit breaker, and `LLM_ENABLED` flag (from `013-langgraph-stategraph-llm`).
- ARQ queue dispatch (from `014-async-arq-dispatch`).
- Agent health endpoint (from `017-agent-health-endpoint`).
- Procurement entities (from `018-procurement-domain`).

This feature does not introduce new infrastructure. It defines a new pipeline variant (`ProcurementGraph`) and new agent specializations, all running inside the existing FastAPI + ARQ + PostgreSQL stack. No prediction may be emitted before the data quality gate from `018-procurement-domain` passes; this preserves the constitution's data-driven decision invariant.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compare offers and recommend the best alternative (Priority: P1)

A buyer triggers an offer comparison for a purchase request that has at least two `validated` quotations. The system runs the procurement graph, normalizes offers (currency, lead time, total cost of ownership), computes a quantitative score per offer, generates a natural-language recommendation justified by the data, and returns the recommended offer plus a ranked list of alternatives.

**Why this priority**: Automated comparison and recommendation is the core MVP capability. The buyer cannot save time or improve clarity without this output.

**Independent Test**: Submit a comparison request for a purchase request with two validated quotations, verify the response contains a `recommended_quotation_id`, a `score_per_quotation` map, and a structured justification, and confirm the LangGraph checkpoint chain is recorded in PostgreSQL.

**Acceptance Scenarios**:

1. **Given** a purchase request with two `validated` quotations and `LLM_ENABLED=true`, **When** the pipeline runs, **Then** it returns a `RecommendedOffer` with `recommended_quotation_id`, `score_per_quotation`, `justification` text, and `provenance_chain` referencing the quotation IDs and rules used.
2. **Given** a purchase request with quotations in different currencies, **When** the pipeline runs, **Then** the offer normalization step converts each total to the request's currency using the tenant's configured exchange-rate source and records the rate timestamp in the provenance chain.
3. **Given** a purchase request whose quotations are all economically equivalent within a 1% band, **When** the pipeline runs, **Then** the recommendation includes a `tie_break_reason` (for example `shorter_lead_time` or `lower_supplier_risk`) and exposes the tie explicitly rather than choosing arbitrarily.

---

### User Story 2 - Justification with verifiable provenance (Priority: P1)

The recommendation includes an explainability artifact that lists which fields drove the decision (price, lead time, payment terms, supplier risk tier), the weights applied, the data source for each input, and any caveats (for example "supplier risk tier is a default because no risk record exists for this supplier"). The artifact is structured (machine-readable) and rendered (human-readable) at the API boundary.

**Why this priority**: The constitution mandates that every recommendation has a complete provenance chain. Without explainability, buyers cannot defend the decision to auditors or stakeholders.

**Independent Test**: Run a comparison and request the explainability artifact through the API. Confirm every numeric input in the artifact maps back to a stored quotation field or supplier attribute and that no element is fabricated.

**Acceptance Scenarios**:

1. **Given** a completed comparison, **When** the buyer fetches the explainability artifact, **Then** every claim in the justification text references a field that exists in the persisted quotation or supplier records.
2. **Given** a quotation field that is missing or estimated, **When** the explainability agent renders the artifact, **Then** the field is tagged `estimated` with the estimation rule and never silently substituted.
3. **Given** a recommendation that contradicts the highest-scoring quotation (for example a low-cost offer was rejected for compliance reasons), **When** the artifact is rendered, **Then** the override reason is captured as `override_rule` with the policy reference.

---

### User Story 3 - Reviewer enforces compliance and budget policy (Priority: P2)

Before a recommendation is released, the `reviewer` agent validates the outcome against tenant policies: budget cap, supplier blacklist or sanctions list, payment-term policy (for example minimum 30-day terms), and risk tier thresholds. If any policy is violated, the reviewer either escalates with a structured reason or downgrades the recommendation to the next compliant offer; the system never silently overrides a Tier 1 policy.

**Why this priority**: The constitution requires `reviewer` approval before any recommendation reaches operators, with explicit escalation reasons on failure paths.

**Independent Test**: Configure a tenant policy that blocks suppliers in country X, run a comparison where the highest-scoring offer is from country X, and verify the recommendation is downgraded with a logged `policy_violation` and the offer reordering is reflected in the response.

**Acceptance Scenarios**:

1. **Given** a tenant budget cap of 10,000 USD, **When** the highest-scoring offer exceeds the cap, **Then** the reviewer downgrades the recommendation to the next compliant offer or escalates with `escalation_reason: budget_exceeded` if no compliant offer exists.
2. **Given** a supplier on the tenant's blacklist, **When** that supplier's quotation is the lowest cost, **Then** the reviewer rejects the offer, records `policy_violation: blacklisted_supplier`, and recommends the next compliant offer.
3. **Given** all quotations violate tenant policy, **When** the reviewer runs, **Then** the pipeline terminates in `escalated` state with a registered escalation sink and emits the structured reason; no recommendation is released.

---

### User Story 4 - Graceful degradation when LLM unavailable (Priority: P2)

When `LLM_ENABLED=false` or the LLM circuit breaker is open, the pipeline still produces a recommendation using deterministic rules: weighted score on price, lead time, payment terms, and supplier risk tier. The response is tagged `degradation_flags: ["llm_disabled"]` or `["llm_recommendation_fallback"]` so buyers know the recommendation is rule-based.

**Why this priority**: Air-gapped deployments and outage scenarios must still produce useful output. The constitution requires graceful degradation as a Tier 1 invariant.

**Independent Test**: Set `LLM_ENABLED=false`, run a comparison, and verify the pipeline still returns a `RecommendedOffer` whose `justification` was generated by the rule-based template and whose `degradation_flags` include `llm_disabled`.

**Acceptance Scenarios**:

1. **Given** `LLM_ENABLED=false`, **When** the pipeline runs, **Then** the response includes a deterministic recommendation, `degradation_flags: ["llm_disabled"]`, and a justification synthesized from a rule template; no LLM API call is attempted.
2. **Given** the LLM circuit breaker is open mid-execution, **When** the recommendation agent runs, **Then** it falls back to the rule-based template and tags `llm_recommendation_fallback` without breaking the graph.
3. **Given** the recommendation is rule-based, **When** the buyer fetches the response, **Then** the UI rendering surface (defined in `021-procurement-apex-application`) displays the degradation tag prominently.

---

### Edge Cases

- What happens when only one validated quotation exists (no comparison possible)?
- How does the pipeline behave when supplier risk data is stale or missing for the chosen supplier?
- What happens when exchange rates are stale and currency normalization is uncertain?
- How does the pipeline resume from checkpoint if the worker dies during scoring?
- What happens when policy configuration changes mid-execution (config version pinning)?
- How does the pipeline behave under air-gapped mode with no external rate or risk providers?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a procurement comparison endpoint that, given a `purchase_request_id`, dispatches a job to the ARQ queue to run the procurement graph.
- **FR-002**: System MUST refuse to dispatch the comparison if fewer than two quotations are in status `validated` or if the request is not in status `ready_for_review`.
- **FR-003**: The procurement graph MUST be implemented as a LangGraph `StateGraph(ProcurementState)` with five nodes: `offer_analyzer`, `offer_scorer`, `recommendation_engine`, `explainability`, `reviewer`.
- **FR-004**: `offer_analyzer` MUST normalize quotations (currency, units, lead time) and emit a structured comparison table; the agent MUST flag any input it could not normalize and not silently coerce.
- **FR-005**: `offer_scorer` MUST compute a numeric score per quotation using a configurable weight vector (price, lead time, payment terms, supplier risk tier) stored in versioned PostgreSQL config (per `011-config-management`).
- **FR-006**: `recommendation_engine` MUST call the LLM adapter when `LLM_ENABLED=true` to produce a natural-language justification grounded in the comparison table; it MUST fall back to a deterministic template otherwise.
- **FR-007**: `explainability` MUST emit a structured artifact listing every input, weight, source, and any `estimated` or `override_rule` tag.
- **FR-008**: `reviewer` MUST validate the recommendation against tenant policy (budget cap, blacklist, payment-term floor, risk tier ceiling) and either approve, downgrade with a logged reason, or escalate with `escalation_reason`.
- **FR-009**: System MUST checkpoint state after each node using `langgraph-checkpoint-postgres`; the graph MUST resume from the last checkpoint on worker restart.
- **FR-010**: System MUST refuse to read any quotation whose status is not `validated`; quarantined quotations MUST be ignored.
- **FR-011**: System MUST persist the resulting `Recommendation` in PostgreSQL with full provenance chain, scores, justification, degradation flags, and a link back to the source `PurchaseRequest`.
- **FR-012**: System MUST emit OpenTelemetry traces for the full graph and Prometheus metrics for graph latency, per-node latency, fallback activation count, and policy override count.
- **FR-013**: System MUST honor `LLM_ENABLED=false` and circuit breaker state, falling back to deterministic recommendation logic with explicit `degradation_flags`.
- **FR-014**: System MUST keep the procurement graph behind a feature flag `procurement_pipeline_enabled` (default `false`) and disable it per tenant unless explicitly enabled.
- **FR-015**: System MUST never auto-approve or send any external communication on the success path; the pipeline output is a recommendation, not an action.
- **FR-016**: System MUST function in air-gapped mode using locally cached exchange rates and supplier risk records; staleness MUST be reported in the provenance chain.

### Key Entities

- **ProcurementState**: TypedDict for the procurement pipeline. Fields: `tenant_id`, `team_id`, `purchase_request_id`, `quotations` (list of validated quotation snapshots), `comparison_table`, `score_per_quotation`, `recommended_quotation_id`, `justification`, `explainability_artifact`, `policy_check_result`, `escalation_reason`, `degradation_flags`, `provenance_chain`, `thread_id`, `checkpoint_id`.
- **Recommendation**: Persisted output of the pipeline. Fields: `recommendation_id`, `purchase_request_id`, `recommended_quotation_id`, `ranked_quotation_ids`, `score_per_quotation`, `justification`, `policy_check_result`, `degradation_flags`, `provenance_chain`, `created_at`, `pipeline_version`, `config_version`.
- **ProcurementPolicyConfig**: Versioned config stored in PostgreSQL. Fields: `policy_id`, `tenant_id`, `weight_vector`, `budget_caps_per_category`, `blacklist`, `min_payment_term_days`, `max_supplier_risk_tier`, `version`, `effective_from`, `superseded_by`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of comparison runs that emit a `Recommendation` traverse `offer_analyzer`, `offer_scorer`, `recommendation_engine`, `explainability`, and `reviewer` in order with checkpoints recorded.
- **SC-002**: Zero recommendations are released that include a quarantined quotation; CI verifies this with an automated regression test.
- **SC-003**: Every `Recommendation` row has a non-empty `provenance_chain` and a non-empty `policy_check_result`.
- **SC-004**: P95 end-to-end pipeline latency is under 60 seconds per comparison with `LLM_ENABLED=true`, and under 5 seconds with `LLM_ENABLED=false`.
- **SC-005**: When the LLM is disabled or the circuit breaker is open, the pipeline still completes successfully and the response carries the correct `degradation_flags` in 100% of regression tests.
- **SC-006**: Policy violations on the lowest-cost offer trigger downgrade or escalation in 100% of regression tests; zero recommendations are released that violate Tier 1 tenant policies.
- **SC-007**: In air-gapped mode the pipeline completes using cached exchange rates and risk data with explicit staleness reporting; CI runs the full pipeline with no external network access.
