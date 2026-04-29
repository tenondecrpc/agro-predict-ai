# Feature Specification: Multi-Tenancy

**Feature Branch**: `007-multi-tenancy`  
**Created**: 2026-04-28  
**Status**: Implemented  
**Input**: Tenant and team isolation across credentials, data, models, budgets, and queue behavior

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tenant data isolation (Priority: P1)

Each tenant's data is completely isolated from other tenants. Predictions, models, configurations, and audit logs are scoped to a specific tenant. No tenant can access another tenant's data through any API, database query, or agent execution path.

**Why this priority**: Multi-tenancy is a Tier 1 non-negotiable. Data leakage between tenants is a critical security and compliance failure.

**Independent Test**: Can be fully tested by creating two tenants, ingesting data for each, running predictions, and verifying neither tenant can access the other's data.

**Acceptance Scenarios**:

1. **Given** two tenants exist, **When** tenant A queries predictions, **Then** only tenant A's predictions are returned.
2. **Given** a model is registered under tenant A, **When** tenant B attempts to use the model, **Then** the system denies access.
3. **Given** an agent executes a prediction for tenant A, **When** the agent accesses data, **Then** only tenant A's data is visible to the agent.

---

### User Story 2 - Team-level resource quotas (Priority: P2)

Within a tenant, teams have individual resource quotas for prediction requests, model training jobs, and storage. When a team exceeds its quota, further requests are rate-limited or rejected with a clear quota-exceeded message.

**Why this priority**: Resource quotas prevent a single team from consuming all system resources and affecting other teams within the same tenant.

**Independent Test**: Can be tested by configuring a team quota, exhausting it with requests, and verifying subsequent requests are rate-limited.

**Acceptance Scenarios**:

1. **Given** a team has a prediction quota of 100 per hour, **When** the team submits 101 requests, **Then** the 101st request is rejected with a quota-exceeded error.
2. **Given** a team's quota is exhausted, **When** the quota window resets, **Then** the team can submit requests again.
3. **Given** multiple teams within a tenant, **When** team A exhausts its quota, **Then** team B's requests are unaffected.

---

### User Story 3 - Tenant-scoped model and budget isolation (Priority: P3)

Each tenant has its own model registry and budget allocation. Models trained under one tenant are not visible to other tenants. Budget consumption (compute, storage, API calls) is tracked per tenant and per team.

**Why this priority**: Budget isolation ensures fair resource allocation and prevents cross-tenant cost attribution errors.

**Independent Test**: Can be tested by registering models under different tenants, verifying model visibility is scoped, and checking budget tracking accuracy.

**Acceptance Scenarios**:

1. **Given** a model is registered under tenant A, **When** tenant B lists models, **Then** tenant A's model is not visible.
2. **Given** a tenant's budget is exhausted, **When** the tenant submits a prediction request, **Then** the system rejects the request with a budget-exceeded error.
3. **Given** budget tracking is enabled, **When** an admin views the budget dashboard, **Then** consumption is accurately reported per tenant and per team.

---

### Edge Cases

- What happens when a tenant is deleted while predictions are in progress?
- How does the system handle a request with an invalid or missing tenant ID?
- What happens when a team is moved from one tenant to another?
- How does the system handle cross-tenant data in the Oracle APEX integration?
- What happens when the tenant isolation layer fails (e.g., a bug in the tenant-scoping middleware)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST scope all data (predictions, models, configurations, audit logs) to a specific tenant.
- **FR-002**: System MUST enforce tenant isolation at the API layer, database query layer, and agent execution layer.
- **FR-003**: System MUST support team-level resource quotas within a tenant for predictions, model training, and storage.
- **FR-004**: System MUST rate-limit or reject requests when a team exceeds its quota.
- **FR-005**: System MUST track budget consumption per tenant and per team.
- **FR-006**: System MUST reject requests when a tenant's budget is exhausted.
- **FR-007**: System MUST scope model registry to individual tenants (no cross-tenant model visibility).
- **FR-008**: System MUST scope credential storage to individual tenants (no shared credentials).
- **FR-009**: System MUST scope queue behavior to individual tenants (separate ARQ queues per tenant).
- **FR-010**: System MUST audit all tenant-scoped access attempts, including denied cross-tenant access.

### Key Entities

- **Tenant**: Represents a customer organization. Key attributes: tenant_id, name, status, created_at, resource_quotas, budget_limit, budget_consumed.
- **Team**: Represents a team within a tenant. Key attributes: team_id, tenant_id, name, status, resource_quotas, budget_limit, budget_consumed.
- **TenantIsolationContext**: Represents the tenant context for a request. Key attributes: tenant_id, team_id, request_id, authenticated_at, scope_level.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero cross-tenant data access events in production (verified by audit log analysis).
- **SC-002**: Tenant isolation enforcement adds less than 5ms overhead per request (P95).
- **SC-003**: Quota enforcement is accurate within 1% of configured limits.
- **SC-004**: Budget tracking is accurate within 1% of actual resource consumption.
- **SC-005**: Tenant deletion completes within 60 seconds with complete data removal (verified by audit).
