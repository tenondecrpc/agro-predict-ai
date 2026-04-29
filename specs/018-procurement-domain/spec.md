# Feature Specification: Procurement Domain and Quotation Ingestion

**Feature Branch**: `018-procurement-domain`
**Created**: 2026-04-29
**Status**: Draft
**Input**: Adapt AgroPredict AI to support an Intelligent Purchasing Copilot. This first feature establishes the procurement domain model (purchase requests, suppliers, quotations) and the ingestion path so downstream AI features can compare offers and generate negotiation messages.

## Context

The Intelligent Purchasing Copilot extends AgroPredict AI from agricultural and logistics prediction into procurement decision support. Buyers must register a purchase request, capture quotations from multiple suppliers, and feed validated procurement data to the LangGraph pipeline. Spec `006-oracle-apex-integration` already provides a read-only Oracle APEX adapter and audited write-back; this feature reuses that contract and adds procurement-specific entities, validation, and APIs.

The data plane defined here is the foundation for:

- `019-procurement-decision-pipeline`: AI-driven offer comparison and recommendation.
- `020-procurement-negotiation-assistant`: AI-assisted negotiation message generation.
- `021-procurement-apex-application`: Oracle APEX UI that captures user input and renders results.

Procurement data must remain tenant-scoped, auditable, and validated before any AI agent consumes it. The data quality gate from `.specify/memory/constitution.md` applies: no recommendation may be emitted from data that has not passed validation.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register a purchase request (Priority: P1)

A buyer submits a purchase request describing what they need to acquire (item description, quantity, target delivery date, budget cap, business unit). The system validates the request, persists it under the buyer's tenant and team, and returns a `purchase_request_id` that can be referenced when uploading quotations.

**Why this priority**: Every downstream capability (quotation capture, comparison, recommendation, negotiation) is anchored to a purchase request. Without registration, the copilot has nothing to reason about.

**Independent Test**: Submit a purchase request through the API, confirm a record is created in PostgreSQL with the correct tenant and team scope, and verify the request is visible only to authorized users in that tenant.

**Acceptance Scenarios**:

1. **Given** an authenticated buyer in tenant T, **When** the buyer submits a valid purchase request, **Then** the system stores it under tenant T with status `draft` and returns `purchase_request_id`.
2. **Given** a purchase request with missing required fields (item description, quantity, target delivery date), **When** the buyer submits it, **Then** the system rejects the request with a structured validation error and stores nothing.
3. **Given** a purchase request whose budget cap is below zero or whose target delivery date is in the past, **When** the buyer submits it, **Then** the system rejects the request and emits an audit event tagged `procurement.request.rejected`.

---

### User Story 2 - Register suppliers and upload quotations (Priority: P1)

A buyer registers one or more suppliers and uploads a quotation per supplier against an existing purchase request. Each quotation captures unit price, currency, total amount, payment terms, lead time in days, validity window, and any free-text terms. The system stores the quotation, links it to the purchase request, and records the upload in the audit log.

**Why this priority**: Comparison and recommendation are impossible without at least two competing quotations. This is the second mandatory primitive of the MVP.

**Independent Test**: Upload two quotations for the same purchase request, confirm both are stored with correct linkage, and verify the audit log captures who uploaded each quotation and when.

**Acceptance Scenarios**:

1. **Given** a purchase request in status `draft`, **When** a buyer uploads a quotation referencing a registered supplier, **Then** the system persists the quotation linked to the purchase request and records `procurement.quotation.uploaded` in the audit log.
2. **Given** a quotation referencing a supplier that does not exist for the buyer's tenant, **When** the buyer uploads the quotation, **Then** the system rejects the upload and surfaces a `supplier_not_found` error.
3. **Given** a quotation whose currency is not registered in the tenant's allowed currency list, **When** the buyer uploads it, **Then** the system rejects the upload with a `currency_not_supported` error.
4. **Given** an existing purchase request with two quotations, **When** the buyer transitions the request to status `ready_for_review`, **Then** the system requires at least two non-expired quotations and refuses the transition otherwise.

---

### User Story 3 - Quotation data quality gate (Priority: P2)

Before any AI agent reads a quotation, the system runs validation checks: required fields present, currency normalized, units consistent across quotations of the same request, validity window not expired, and lead time within plausible range. Quotations that fail are quarantined and tagged with the failing rule. Buyers see the failure reason and can correct the quotation.

**Why this priority**: The constitution requires that every prediction or recommendation traces to validated data. Without this gate, the downstream AI pipeline cannot honor the data quality invariant.

**Independent Test**: Upload a quotation with an expired validity window, verify it is quarantined with `quality_flag: validity_expired`, attempt to include it in a comparison, and confirm the comparison API refuses to include quarantined quotations.

**Acceptance Scenarios**:

1. **Given** a quotation with an expired validity window, **When** the data quality gate runs, **Then** the quotation is moved to status `quarantined` with reason `validity_expired` and is not returned by the comparison endpoint.
2. **Given** a set of quotations on the same request whose unit measures disagree (kg vs. lb), **When** the gate runs, **Then** the conflicting quotations are flagged `unit_mismatch` and the system suggests a unit normalization.
3. **Given** a quotation that passes all checks, **When** the gate runs, **Then** the quotation transitions to status `validated` and becomes eligible for AI comparison.

---

### User Story 4 - Tenant and team isolation for procurement data (Priority: P2)

A user in tenant A and team A1 cannot see, read, modify, or reference purchase requests, suppliers, or quotations belonging to tenant B or to team A2 within tenant A unless explicit cross-team access is granted. All procurement queries enforce tenant and team scope at the data layer.

**Why this priority**: Multi-tenancy and team isolation are Tier 1 non-negotiables. A leak of a competing business unit's quotations would be a critical security incident.

**Independent Test**: Authenticate as a user in tenant A team A2 and attempt to read a purchase request belonging to tenant A team A1. Confirm the API returns `404 Not Found` (not `403 Forbidden`, to avoid existence leaks) and the access attempt is logged.

**Acceptance Scenarios**:

1. **Given** a purchase request scoped to tenant A team A1, **When** a user in tenant A team A2 queries it, **Then** the system returns `404` and logs `procurement.access.denied`.
2. **Given** a quotation scoped to tenant A, **When** a user in tenant B queries it, **Then** the system returns `404` and the cross-tenant attempt raises a security alert.
3. **Given** a tenant administrator grants team A2 read access to team A1's purchase requests, **When** a user in team A2 queries those requests, **Then** access is allowed and recorded in the audit log.

---

### Edge Cases

- What happens when a supplier is deactivated while a quotation referencing them is still active?
- How does the system handle a quotation uploaded as a PDF or spreadsheet attachment versus structured fields?
- How does the system reconcile two quotations from the same supplier on the same request (latest wins, or both kept)?
- What happens when a tenant rotates its credential set mid-upload?
- How is purchase request data deleted when a tenant's data retention policy fires?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST expose a REST API to create, read, update, and cancel purchase requests scoped to a tenant and team.
- **FR-002**: System MUST expose a REST API to register and deactivate suppliers scoped to a tenant.
- **FR-003**: System MUST expose a REST API to upload quotations linked to a purchase request and a supplier.
- **FR-004**: System MUST validate purchase requests for required fields, non-negative budget cap, and a target delivery date that is not in the past.
- **FR-005**: System MUST validate quotations for required fields, supported currency, plausible lead time, and an unexpired validity window.
- **FR-006**: System MUST run a data quality gate on every quotation and tag failed quotations with structured `quality_flags` (for example `validity_expired`, `unit_mismatch`, `currency_not_supported`).
- **FR-007**: System MUST refuse to surface quarantined quotations to downstream AI pipelines.
- **FR-008**: System MUST persist all procurement entities in PostgreSQL using existing schemas extended through expand/contract migrations - no new datastore.
- **FR-009**: System MUST enforce tenant and team isolation at the query layer; cross-tenant or unauthorized cross-team queries MUST return `404` and log a security event.
- **FR-010**: System MUST emit audit events for every create, update, transition, quarantine, and access-denied action with actor, tenant, team, timestamp, and entity references.
- **FR-011**: System MUST allow ingestion of procurement data from Oracle APEX through the existing read-only adapter (`006-oracle-apex-integration`); APEX data ingested this way MUST traverse the same data quality gate as direct API uploads.
- **FR-012**: System MUST support attachment uploads (PDF, spreadsheet) for a quotation, store them in customer-owned object storage, and record the artifact reference on the quotation; attachment processing or extraction is out of scope for this feature.
- **FR-013**: System MUST honor tenant data retention and deletion policies for procurement entities; deletions MUST cascade to quotations, attachments references, and audit summaries while preserving immutable audit records as required by policy.
- **FR-014**: System MUST expose a feature flag `procurement_domain_enabled` (default `false`) so the procurement APIs do not surface to tenants that have not opted in.

### Key Entities

- **PurchaseRequest**: A buyer's request to procure goods or services. Attributes: `request_id`, `tenant_id`, `team_id`, `requested_by`, `item_description`, `quantity`, `unit_of_measure`, `target_delivery_date`, `budget_cap`, `currency`, `status` (`draft` | `ready_for_review` | `recommended` | `closed` | `cancelled`), `created_at`, `updated_at`.
- **Supplier**: A company a buyer can solicit quotations from. Attributes: `supplier_id`, `tenant_id`, `legal_name`, `tax_id`, `contact_email`, `contact_phone`, `country`, `status` (`active` | `inactive`), `risk_tier`, `created_at`.
- **Quotation**: A supplier's offer for a purchase request. Attributes: `quotation_id`, `request_id`, `supplier_id`, `unit_price`, `currency`, `total_amount`, `payment_terms`, `lead_time_days`, `validity_until`, `terms_text`, `attachment_ref`, `status` (`uploaded` | `validated` | `quarantined`), `quality_flags`, `created_by`, `created_at`.
- **ProcurementAuditEvent**: Audit record for any change to procurement state. Attributes: `event_id`, `tenant_id`, `team_id`, `actor`, `action`, `entity_type`, `entity_id`, `payload_summary`, `occurred_at`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of purchase requests, suppliers, and quotations created via API are scoped to the correct tenant and team and pass an automated isolation regression test in CI.
- **SC-002**: 100% of quotations exposed to downstream AI agents have status `validated`; zero quarantined quotations leak into comparison or recommendation flows.
- **SC-003**: Purchase request creation through completed quotation upload (two suppliers) takes under 60 seconds for a buyer using the API directly.
- **SC-004**: Every state transition produces a `ProcurementAuditEvent` with full actor, tenant, team, and entity references; CI verifies zero untracked transitions.
- **SC-005**: P95 latency for `GET /procurement/requests/{id}` under nominal load is under 200 ms.
- **SC-006**: Data deletion driven by tenant retention policy completes within the SLA defined by `010-security-secrets` and leaves no orphaned attachment references.
