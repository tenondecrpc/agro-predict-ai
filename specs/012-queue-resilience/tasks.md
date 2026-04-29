# Tasks: Queue and Resilience

---

## User Story 1 - ARQ async processing (Priority: P1)

### US1-T1: Define ARQ job models
- **Verify**: ARQJob model validates correctly

---

## User Story 2 - Dead letter queue (Priority: P2)

### US2-T1: Implement DLQ models
- **Verify**: DeadLetterJob preserves failure context

---

## User Story 3 - Graceful shutdown (Priority: P3)

### US3-T1: Implement checkpoint models
- **Verify**: Checkpoint state enables resume

---

## Verification & Archive

### V-T1: Run lint
### V-T2: Run all queue tests
### V-T3: Archive
