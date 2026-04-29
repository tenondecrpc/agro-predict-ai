# Feature Specification: AI-Assisted Negotiation Message

**Feature Branch**: `020-procurement-negotiation-assistant`
**Created**: 2026-04-29
**Status**: Draft
**Input**: Add an AI-assisted negotiation capability on top of the procurement decision pipeline. Given a `Recommendation` (from `019-procurement-decision-pipeline`) and a target supplier, the system generates a personalized negotiation message that asks for better commercial conditions. The buyer reviews, edits, and decides whether to send the message; sending is always explicit and audited.

## Context

The Intelligent Purchasing Copilot is most useful when it shortens the path from "we have offers" to "we got better terms." This feature introduces a negotiation message generator that:

- Reuses the existing LLM adapter (`013-langgraph-stategraph-llm`) and its secure credential contract.
- Reads from a persisted `Recommendation` and the underlying `PurchaseRequest`, `Quotation`, and `Supplier` records.
- Produces a natural-language draft message tailored to the supplier and the negotiation objectives chosen by the buyer (price, payment terms, lead time, bundle discount).
- Never sends the message by itself. Sending is opt-in, explicit, audited, and may be disabled entirely on air-gapped deployments.

This feature does not introduce new datastores. Negotiation messages and audit records live in PostgreSQL.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate a personalized negotiation message (Priority: P1)

A buyer, looking at a recommendation, asks the copilot to draft a negotiation message for a specific supplier (typically the recommended one or a runner-up they want to push back on). The buyer chooses one or more negotiation objectives (lower price, longer payment terms, faster lead time, bundle discount). The system produces a personalized draft message that references the supplier, the quoted figures, the buyer's objectives, and the comparison context.

**Why this priority**: Drafting negotiation messages by hand is repetitive and time-consuming. Automating the draft is the primary value proposition stated in the challenge.

**Independent Test**: Trigger negotiation message generation for a known recommendation and a known target supplier, confirm the response includes a draft text that quotes the supplier's specific offer figures, references the buyer's chosen objectives, and never references a competing supplier's name.

**Acceptance Scenarios**:

1. **Given** a `Recommendation` and a target supplier with a `validated` quotation on the same purchase request, **When** the buyer triggers message generation with the objective `lower_price`, **Then** the system returns a draft message that quotes the supplier's unit price and proposes a counter-offer derived from the comparison context, without disclosing competing suppliers' names or proprietary figures.
2. **Given** the buyer selects multiple objectives (`lower_price`, `longer_payment_terms`), **When** the system generates the draft, **Then** the message addresses each objective in a structured way and ranks them by buyer-specified priority.
3. **Given** the supplier's preferred language is set on the supplier record, **When** the message is generated, **Then** the draft is returned in that language (Spanish or English at MVP), defaulting to English if no preference is set.

---

### User Story 2 - Buyer edits and approves the draft before sending (Priority: P1)

The system never sends a negotiation message automatically. The generated draft is returned to the buyer, who can edit any part of the message, append context, or discard the draft entirely. Sending requires an explicit action and is recorded in the audit log with the final approved text, the actor, the timestamp, and the channel (email, APEX export, manual copy).

**Why this priority**: The constitution forbids automated outbound communication on the success path; the buyer must remain in control. This invariant is also a basic safeguard for tenant reputation.

**Independent Test**: Generate a draft, edit the body, submit it for sending, and verify the audit record stores the final edited body (not the original draft) along with the approving actor and timestamp.

**Acceptance Scenarios**:

1. **Given** a generated draft, **When** the buyer edits the body and submits the message for sending, **Then** the system records the final body, the actor, the timestamp, and the chosen channel in the audit log.
2. **Given** the buyer chooses channel `manual_copy`, **When** the message is approved, **Then** no outbound delivery is attempted, the message is stored as `approved`, and the audit log marks it `delivery_method: manual_copy`.
3. **Given** the buyer discards the draft, **When** the discard action runs, **Then** the system records `negotiation.draft.discarded` in the audit log and retains no draft body beyond the configured retention window.

---

### User Story 3 - Tone, channel, and policy controls per tenant (Priority: P2)

Tenants configure a tone preset (`formal`, `neutral`, `friendly`), a default channel (`email_outbox`, `apex_export`, `manual_copy`), and policy clauses that must always or never appear (for example, mandatory anti-bribery clause, prohibited promises). The generator respects these controls; the reviewer agent rejects or rewrites drafts that violate clause policy.

**Why this priority**: Different organizations have different procurement cultures and compliance requirements. Without tenant controls, the assistant cannot ship across heterogeneous customers.

**Independent Test**: Configure a tenant policy that requires an anti-bribery clause and forbids price-fixing language, generate a draft, and confirm the clause is present and the forbidden language is absent in the final draft.

**Acceptance Scenarios**:

1. **Given** a tenant configured with `tone: formal` and a mandatory anti-bribery clause, **When** the system generates a draft, **Then** the draft uses formal language and includes the mandatory clause verbatim.
2. **Given** the LLM produces a draft that violates clause policy, **When** the reviewer runs, **Then** the system either regenerates with the violation removed or rejects the draft with `policy_violation: forbidden_clause`.
3. **Given** the tenant disables outbound channels (air-gapped or compliance lockdown), **When** the buyer attempts to send, **Then** only `manual_copy` is offered and the system refuses any other channel selection.

---

### User Story 4 - Graceful degradation when the LLM is disabled (Priority: P3)

When `LLM_ENABLED=false` or the LLM circuit is open, the assistant returns a structured rule-based draft (filled-in template) and tags the response `degradation_flags: ["llm_disabled"]` or `["llm_negotiation_fallback"]`. The buyer can still edit, approve, and send the message.

**Why this priority**: Air-gapped deployments and outages must not block the buyer from sending a negotiation message. The constitution requires graceful degradation.

**Independent Test**: Set `LLM_ENABLED=false`, generate a negotiation message, and verify the response carries a template-based body and the correct `degradation_flags`.

**Acceptance Scenarios**:

1. **Given** `LLM_ENABLED=false`, **When** the buyer requests a draft, **Then** the system returns a deterministic template that interpolates supplier figures and objectives, with `degradation_flags: ["llm_disabled"]`.
2. **Given** the LLM circuit is open mid-request, **When** the assistant retries, **Then** it falls back to the template draft and tags `llm_negotiation_fallback`.
3. **Given** a degraded draft, **When** the buyer approves and sends it, **Then** the audit record stores the degradation tags alongside the approved body.

---

### Edge Cases

- What happens when the buyer asks for a draft against a supplier who has no `validated` quotation on the request?
- How does the assistant handle quotations in currencies the tenant does not support?
- What happens when the buyer selects contradictory objectives (for example shorter lead time and a much lower price)?
- How does the system handle attempts to insert PII or proprietary data from a competing supplier into the draft?
- What happens when the chosen channel (for example `email_outbox`) is configured but the SMTP backend is unreachable?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose an API to generate a negotiation message draft for a given `recommendation_id` and `supplier_id`, accepting one or more objectives from a fixed enumeration.
- **FR-002**: System MUST refuse to generate a draft if the target supplier has no `validated` quotation on the underlying purchase request.
- **FR-003**: System MUST never include the names, prices, or terms of competing suppliers in the generated body; only the buyer's own constraints (such as budget cap and target delivery date) may be referenced.
- **FR-004**: System MUST call the LLM adapter when `LLM_ENABLED=true` and fall back to a deterministic rule-based template otherwise, tagging `degradation_flags` accordingly.
- **FR-005**: System MUST persist every draft, edited revision, approval, send attempt, and discard event in PostgreSQL with full audit metadata (actor, tenant, team, timestamp, channel).
- **FR-006**: System MUST require explicit buyer approval before any outbound delivery; no draft may be sent automatically.
- **FR-007**: System MUST support configurable channels (`email_outbox`, `apex_export`, `manual_copy`) and refuse channels disabled by tenant policy or by the air-gapped deployment profile.
- **FR-008**: System MUST run a reviewer pass on the LLM output that enforces tenant clause policy (mandatory clauses, forbidden language) and either regenerates or rejects drafts that violate policy.
- **FR-009**: System MUST preserve language preference per supplier (Spanish or English at MVP, with extraction infrastructure ready for future locales) and emit drafts in the chosen language.
- **FR-010**: System MUST emit OpenTelemetry traces for every generation, edit, approval, and send action, plus Prometheus metrics for generation latency, fallback rate, and policy rejection rate.
- **FR-011**: System MUST keep the negotiation assistant behind a feature flag `procurement_negotiation_enabled` (default `false`) with a per-tenant toggle.
- **FR-012**: System MUST honor data retention policy for negotiation messages, including automatic purge of drafts and audit summaries beyond the retention window, while preserving immutable audit records as required.
- **FR-013**: System MUST NOT log raw LLM API keys, supplier credentials, or buyer access tokens; all sensitive values MUST be redacted in trace and log output.
- **FR-014**: System MUST allow tenants to disable outbound delivery entirely (air-gapped or compliance lockdown) so that only `manual_copy` is available.

### Key Entities

- **NegotiationMessage**: A drafted, edited, approved, or sent message. Fields: `message_id`, `tenant_id`, `team_id`, `recommendation_id`, `purchase_request_id`, `supplier_id`, `objectives`, `tone_preset`, `language`, `body_draft`, `body_final`, `status` (`draft` | `approved` | `sent` | `discarded`), `channel`, `degradation_flags`, `created_by`, `approved_by`, `created_at`, `approved_at`, `sent_at`.
- **NegotiationPolicyConfig**: Versioned tenant configuration. Fields: `policy_id`, `tenant_id`, `tone_preset`, `mandatory_clauses`, `forbidden_clauses`, `allowed_channels`, `version`, `effective_from`, `superseded_by`.
- **NegotiationAuditEvent**: Audit record. Fields: `event_id`, `tenant_id`, `team_id`, `actor`, `action`, `message_id`, `payload_summary`, `occurred_at`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of generated drafts contain at least one quoted figure from the target supplier's quotation; CI verifies via regression test against a golden corpus.
- **SC-002**: Zero generated drafts disclose a competing supplier's name, price, or terms; an automated test corpus verifies this on every CI run.
- **SC-003**: 100% of approved messages carry a complete audit record with actor, tenant, team, timestamp, channel, and final body.
- **SC-004**: P95 generation latency is under 30 seconds with `LLM_ENABLED=true` and under 1 second with `LLM_ENABLED=false`.
- **SC-005**: When the LLM is disabled, the assistant still produces a usable template draft with the correct `degradation_flags` in 100% of regression tests.
- **SC-006**: Tenants on air-gapped profiles see only `manual_copy` as an available channel; CI enforces this configuration constraint.
- **SC-007**: 0 incidents per quarter where a draft is sent without explicit buyer approval (target: 0; alert at 1).
