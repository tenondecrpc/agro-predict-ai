# Tasks: Oracle APEX Integration

---

## User Story 1 - Read-only data synchronization (Priority: P1)

### US1-T1: Define APEX adapter models
- **Verify**: OracleAPEXConnection, SyncJob models validate correctly

### US1-T2: Implement APEX client with circuit breaker
- **Verify**: Client fetches data, handles failures, tracks circuit state

### US1-T3: Implement sync endpoint
- **Verify**: POST /api/v1/apex/sync triggers data pull from APEX

---

## User Story 2 - Audited write-back (Priority: P2)

### US2-T1: Implement write-back service
- **Verify**: Write-back requires operator approval, logs audit

### US2-T2: Implement write-back endpoint
- **Verify**: POST /api/v1/apex/writeback with approval check

---

## User Story 3 - Circuit breaker (Priority: P3)

### US3-T1: Implement circuit breaker state machine
- **Verify**: Open/closed/half-open transitions

### US3-T2: Expose circuit breaker state
- **Verify**: GET /api/v1/apex/circuit returns current state

---

## Verification & Archive

### V-T1: Run lint
### V-T2: Run all APEX integration tests
### V-T3: Archive
