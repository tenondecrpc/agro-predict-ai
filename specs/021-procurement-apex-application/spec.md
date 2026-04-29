# Feature Specification: Oracle APEX Procurement Copilot Application

**Feature Branch**: `021-procurement-apex-application`
**Created**: 2026-04-29
**Status**: Draft
**Input**: Build the Oracle APEX-side application that closes the loop on the Intelligent Purchasing Copilot. The APEX app captures purchase requests and quotations, calls the backend procurement APIs (`018-procurement-domain`, `019-procurement-decision-pipeline`, `020-procurement-negotiation-assistant`), and renders comparisons, recommendations, and negotiation messages to buyers.

## Context

The challenge requires the user-facing application to live in Oracle APEX. The existing AgroPredict AI Vite + React frontend remains the operator and admin surface; APEX hosts the buyer-facing procurement workflow. The data flow follows the constitution's invariants:

- The APEX app writes to its own APEX-managed tables for purchase requests, suppliers, and quotations.
- The backend ingests APEX data through the existing read-only adapter (`006-oracle-apex-integration`).
- The backend writes recommendations and negotiation messages back to APEX through audited write-back, also defined in `006-oracle-apex-integration`.
- The buyer-facing UI never queries the application's PostgreSQL directly; it reads back-written results from its APEX tables or calls the backend HTTP APIs.

Accessibility constraints from the constitution apply: keyboard reachability of all interactive elements, no color-only state, AA text contrast, and `prefers-reduced-motion`. APEX themes must be customized to honor these, since default APEX components do not always meet them.

The APEX app is shipped as a packaged application export (`.sql`) under `operations/apex/` and installable on customer-owned APEX instances. No vendor-hosted APEX environment is part of this product.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register a purchase request and upload quotations from APEX (Priority: P1)

A buyer logs in to the APEX application, opens the "New Purchase Request" page, fills in item description, quantity, target delivery date, and budget cap, and submits the request. From the request detail page they register suppliers (or pick from existing tenant suppliers), upload quotations (manual entry plus optional file attachment), and transition the request to `ready_for_review`.

**Why this priority**: This is the core data-capture path. Without it, the backend has no procurement input.

**Independent Test**: Walk through the APEX pages to register a purchase request and upload two quotations; verify the records appear in the APEX tables and are subsequently ingested by the backend through the read-only adapter and pass the data quality gate from `018-procurement-domain`.

**Acceptance Scenarios**:

1. **Given** an authenticated buyer in tenant T, **When** the buyer submits a valid purchase request through APEX, **Then** the record lands in the APEX procurement schema scoped to tenant T and team T1 and is visible in the request list.
2. **Given** a purchase request in `draft`, **When** the buyer uploads two quotations and clicks `Submit for Comparison`, **Then** the request transitions to `ready_for_review`, the backend ingests the data, and the buyer is told the comparison is queued.
3. **Given** a quotation that fails the data quality gate (for example expired validity), **When** the buyer reopens the request, **Then** APEX surfaces the failure reason inline next to the offending quotation.

---

### User Story 2 - Compare offers and view the AI recommendation (Priority: P1)

When the backend completes the comparison, the APEX `Comparison` page shows a side-by-side table of all validated quotations, the AI-generated recommendation (with justification), the ranked alternatives, and any `degradation_flags`. The buyer can drill into the explainability artifact to see input weights and provenance per claim.

**Why this priority**: This is where the buyer experiences the time-saving, decision-clarity benefit promised by the challenge.

**Independent Test**: Trigger a comparison from APEX, wait for the backend to write the recommendation back, refresh the page, and confirm the side-by-side table, the recommendation, the justification, and the explainability link all render correctly.

**Acceptance Scenarios**:

1. **Given** a request whose backend comparison succeeded, **When** the buyer opens the `Comparison` page, **Then** the page shows the comparison table, the recommended quotation highlighted with an icon plus text label (no color-only state), and the justification text.
2. **Given** the recommendation carries `degradation_flags: ["llm_disabled"]`, **When** the page renders, **Then** a banner clearly states that the recommendation is rule-based and does not use LLM reasoning.
3. **Given** the buyer opens the explainability artifact, **When** the artifact renders, **Then** every claim links to a source field (quotation field or supplier attribute) and any `estimated` or `override_rule` tag is visible.

---

### User Story 3 - Generate, edit, and send a negotiation message (Priority: P2)

From the `Comparison` page (or the request detail page), the buyer selects a target supplier, picks one or more negotiation objectives, and clicks `Generate Negotiation Message`. The APEX app calls the backend's negotiation endpoint, displays the draft, lets the buyer edit it, and finally records the buyer's send decision (email, APEX export, manual copy).

**Why this priority**: This is the second value-driving capability of the MVP. It is P2 because the MVP is still useful (comparison and recommendation only) without it.

**Independent Test**: Generate a draft from APEX, edit the body, choose `manual_copy`, approve, and verify the audit log on the backend records the final body, the approving actor, the timestamp, and the channel `manual_copy`.

**Acceptance Scenarios**:

1. **Given** a recommendation, **When** the buyer triggers `Generate Negotiation Message` for the recommended supplier with objective `lower_price`, **Then** APEX displays the draft within the latency budget and offers an edit textarea.
2. **Given** an edited draft and channel `email_outbox` allowed for the tenant, **When** the buyer approves and sends, **Then** APEX records the approval, the backend records the audit event, and the SMTP send attempt result is reported back to the buyer.
3. **Given** an air-gapped tenant where outbound channels are disabled, **When** the buyer attempts to send, **Then** APEX shows only `manual_copy` and disables the other options with explanatory text.

---

### User Story 4 - Audit and decision history per request (Priority: P3)

A reviewer or auditor opens an `Audit` page on a closed purchase request. The page shows the timeline of events (request created, quotations uploaded, comparison run, recommendation issued, message drafted, approved, sent), with actor, timestamp, payload summary, and any policy violations or escalations.

**Why this priority**: Buyers and procurement leads need defensible decision trails. This builds on the audit data that `018`, `019`, and `020` already produce; APEX renders it.

**Independent Test**: Walk an end-to-end flow on a single purchase request and open the `Audit` page; verify every action from `018`, `019`, and `020` appears with correct ordering, actor, and payload.

**Acceptance Scenarios**:

1. **Given** a closed purchase request with a complete history, **When** the reviewer opens the `Audit` page, **Then** every backend audit event appears in chronological order with structured payload summaries.
2. **Given** a recommendation that triggered a `policy_violation` downgrade, **When** the audit page renders, **Then** the violation reason and the applied policy are visible without requiring a backend call from the browser.
3. **Given** the user has read access to the request, **When** they attempt to export the audit trail, **Then** APEX produces a tenant-scoped export (CSV or PDF) and records the export in the audit log itself.

---

### Edge Cases

- What happens when the backend is temporarily unreachable from APEX (network partition, certificate rotation)?
- How does the page render when comparison is still in progress (queued, running, partial result)?
- How does APEX handle a quotation attachment whose object-storage URL has expired?
- What happens when a buyer's tenant entitlement is downgraded mid-session?
- How does APEX behave under air-gapped mode with no LLM-backed responses?
- How does APEX export procurement data while honoring tenant data retention and deletion policies?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: APEX application MUST be packaged as an exportable `.sql` artifact (and supporting scripts) under `operations/apex/` and install cleanly on customer-owned APEX instances.
- **FR-002**: APEX application MUST authenticate buyers using the customer's existing identity provider (OIDC, SAML, or APEX-native auth) and propagate `tenant_id` and `team_id` to backend API calls.
- **FR-003**: APEX application MUST write purchase requests, suppliers, and quotations to APEX-managed tables; the backend ingests these via the existing read-only adapter (`006-oracle-apex-integration`).
- **FR-004**: APEX application MUST refuse to query or render data outside the user's tenant and team scope; cross-tenant access attempts MUST be blocked at the SQL layer and logged.
- **FR-005**: APEX application MUST call backend procurement APIs (`018`, `019`, `020`) over HTTPS using a customer-managed service credential; credentials MUST be stored in the APEX credential store, never inline in page metadata.
- **FR-006**: APEX application MUST display recommendations, justifications, ranked alternatives, and explainability artifacts as written back by the backend; it MUST NOT recompute these client-side.
- **FR-007**: APEX application MUST surface `degradation_flags` prominently (banner, icon plus text) wherever they apply (comparison and negotiation views).
- **FR-008**: APEX application MUST support negotiation message generation, editing, channel selection, approval, and send actions with all events recorded by the backend.
- **FR-009**: APEX application MUST honor accessibility non-negotiables: keyboard reachability of all interactive elements, no color-only state, `prefers-reduced-motion`, and AA text contrast.
- **FR-010**: APEX application MUST function in air-gapped deployments (no internet egress); only the customer-internal backend endpoint and the customer's APEX schema are required.
- **FR-011**: APEX application MUST localize the buyer surface in Spanish and English at MVP, with locale extraction infrastructure ready for additional languages.
- **FR-012**: APEX application MUST expose a `Status` indicator on the comparison page when the backend job is queued, running, completed, or failed; the indicator polls the backend with bounded retries.
- **FR-013**: APEX application MUST be feature-flagged at the page level so customers can roll out individual capabilities (request capture, comparison, negotiation, audit) progressively.
- **FR-014**: APEX application MUST honor tenant data retention and deletion: when the backend purges procurement data per policy, APEX views MUST stop rendering purged records and audit exports MUST tag any redacted entries.
- **FR-015**: APEX application MUST refuse outbound channels disabled by tenant policy and present only `manual_copy` when air-gapped.

### Key Entities

- **APEX schema (procurement)**: Tables `pcp_purchase_request`, `pcp_supplier`, `pcp_quotation`, `pcp_recommendation_view`, `pcp_negotiation_message_view`, and an audit log table; the recommendation and negotiation tables are populated by backend write-back, not by APEX user input.
- **APEX page taxonomy**: `Home`, `Requests List`, `Request Detail`, `Quotation Upload`, `Comparison`, `Negotiation`, `Audit`, `Settings (tenant admin)`.
- **APEX REST consumer**: Configured REST data sources pointing to backend endpoints with the customer-managed service credential and per-call tenant context propagation.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A buyer can register a purchase request with two quotations, run a comparison, and view the AI recommendation in under 5 minutes end-to-end on a customer-owned APEX instance.
- **SC-002**: 100% of comparison and negotiation views display the same recommendation and audit data that the backend persists; an automated parity test runs against the staging APEX instance.
- **SC-003**: APEX pages meet WCAG 2.1 AA non-negotiables (keyboard reachability, no color-only state, AA text contrast, `prefers-reduced-motion`); a manual accessibility checklist is filed with each release.
- **SC-004**: The application installs cleanly on a customer-owned APEX instance with documented prerequisites in under 30 minutes by a procurement IT operator following the runbook.
- **SC-005**: Air-gapped installations complete the full purchase-to-recommendation flow with no external egress; CI runs an air-gapped smoke test in a network-isolated environment.
- **SC-006**: Zero cross-tenant data leaks observed in penetration tests; CI runs a tenant-isolation regression suite against the APEX schema.
- **SC-007**: P95 page load latency for `Comparison` is under 2 seconds with the recommendation already written back.
