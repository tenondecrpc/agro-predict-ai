# Tasks: Multi-Tenancy

---

## User Story 1 - Tenant data isolation (Priority: P1)

### US1-T1: Define tenant and team models
- **Verify**: Tenant, Team, TenantContext Pydantic models

### US1-T2: Implement tenant isolation middleware
- **Verify**: FastAPI middleware extracts tenant_id, rejects invalid

### US1-T3: Verify repository tenant scoping
- **Verify**: All existing repositories filter by tenant_id

---

## User Story 2 - Team-level resource quotas (Priority: P2)

### US2-T1: Implement quota tracker
- **Verify**: Token bucket per team, enforces limits

### US2-T2: Integrate quota into prediction endpoint
- **Verify**: Quota exceeded returns 429

---

## User Story 3 - Budget isolation (Priority: P3)

### US3-T1: Implement budget tracker
- **Verify**: Budget consumed per operation, rejects when exhausted

---

## Verification & Archive

### V-T1: Run lint
### V-T2: Run all multi-tenancy tests
### V-T3: Archive
