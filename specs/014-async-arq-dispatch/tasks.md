# Tasks: Async ARQ Dispatch for Predictions

**Input**: Design documents from `specs/014-async-arq-dispatch/`
**Prerequisites**: spec.md ✅, plan.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Verify ARQ worker process starts correctly with existing config
- [ ] T002 [P] Verify Redis connection is available in test environment

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T003 Wire `redis_client` into `build_predictions_router()` in `backend/src/backend/app.py` - pass the existing Redis client to the predictions router
- [ ] T004 [P] Add `redis_client` as required parameter (no default None) in `build_predictions_router()` in `backend/src/backend/predictions/api.py`

**Checkpoint**: Predictions router has Redis - async path is now active

---

## Phase 3: User Story 1 - Submit prediction and receive immediate job ID (Priority: P1)

**Goal**: POST /api/v1/predictions enqueues job and returns 202 with run_id

### Tests for User Story 1

- [ ] T005 [P] [US1] Add test for 202 with `run_id`, `status`, `status_url` in response in `backend/tests/integration/test_predictions_api.py`
- [ ] T006 [P] [US1] Add test for 503 when Redis is unavailable in `backend/tests/integration/test_predictions_api.py`

### Implementation for User Story 1

- [ ] T007 [US1] Remove synchronous fallback path in `POST /api/v1/predictions` - when `redis_client` is None, return 503 instead of calling `execute()` synchronously in `backend/src/backend/predictions/api.py`
- [ ] T008 [US1] Add proper tenant concurrency counter increment on enqueue and decrement on completion/failure in `backend/src/backend/predictions/api.py` and `backend/src/backend/worker.py`
- [ ] T009 [US1] Read tenant concurrency limit from PostgreSQL config table instead of hardcoding to 10 in `backend/src/backend/predictions/api.py`

**Checkpoint**: POST returns 202, Redis failure returns 503, concurrency enforced

---

## Phase 4: User Story 2 - Poll prediction status until completion (Priority: P1)

**Goal**: GET /api/v1/predictions/{run_id}/status returns running/completed/failed with progress

### Tests for User Story 2

- [ ] T010 [P] [US2] Add test for polling running job (status + current_node) in `backend/tests/integration/test_predictions_api.py`
- [ ] T011 [P] [US2] Add test for polling completed job (full output) in `backend/tests/integration/test_predictions_api.py`
- [ ] T012 [P] [US2] Add test for cross-tenant isolation (404 for wrong tenant) in `backend/tests/integration/test_predictions_api.py`

### Implementation for User Story 2

- [ ] T013 [US2] Refresh TTL on intermediate progress updates in `backend/src/backend/worker.py` (`_update_status()` should call `expire(key, 86400)`)
- [ ] T014 [US2] Add `status=failed` filter support to `GET /api/v1/predictions` list endpoint in `backend/src/backend/predictions/api.py`

**Checkpoint**: Status polling returns live progress, tenant isolation enforced

---

## Phase 5: User Story 3 - Dead letter queue handling for failed jobs (Priority: P2)

**Goal**: Retry endpoint re-enqueues jobs and archives DLQ records

### Tests for User Story 3

- [ ] T015 [P] [US3] Add test for DLQ retry actually re-enqueuing a job in `backend/tests/integration/test_predictions_api.py`
- [ ] T016 [P] [US3] Add test for DLQ job appearing in `GET /api/v1/predictions?status=failed` in `backend/tests/integration/test_predictions_api.py`

### Implementation for User Story 3

- [ ] T017 [US3] Fix `POST /api/v1/predictions/{run_id}/retry` to read from PostgreSQL `dead_letter_records` instead of Redis, re-enqueue via `_enqueue_prediction()`, and archive the DLQ record in `backend/src/backend/predictions/api.py`
- [ ] T018 [US3] Pass full job payload to `capture_terminal_failure()` in `backend/src/backend/worker.py` so DLQ records include the original prediction input

**Checkpoint**: Failed jobs can be retried, DLQ records include full payload

---

## Phase 6: User Story 4 - Weighted fair queueing across tenants (Priority: P3)

**Goal**: Workers dispatch jobs fairly based on tenant weights

### Tests for User Story 4

- [ ] T019 [P] [US4] Add test for fair dispatch across tenants in `backend/tests/unit/test_arq_dispatch.py`

### Implementation for User Story 4

- [ ] T020 [US4] Connect `WeightedFairDispatcher` to ARQ worker job selection logic in `backend/src/backend/persistence/worker.py` or `backend/src/backend/worker.py`
- [ ] T021 [US4] Read per-tenant weights from PostgreSQL config in `backend/src/backend/persistence/worker.py`

**Checkpoint**: Fair dispatch active, tenant weights respected

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T022 [P] Add configurable drain timeout to graceful shutdown hook in `backend/src/backend/worker.py`
- [ ] T023 [P] Add `Retry-After` header logic for 429 responses - ensure it's not hardcoded to 5 seconds in `backend/src/backend/predictions/api.py`
- [ ] T024 Run all backend tests: `uv run --project backend pytest`
- [ ] T025 Run backend lint: `uv run --project backend ruff check backend/src backend/tests`

---

## Dependencies & Execution Order

- **Phase 1 (T001-T002)**: Can start immediately
- **Phase 2 (T003-T004)**: Depends on Phase 1 - **CRITICAL** - unblocks all US
- **US1 (T005-T009)**: Depends on Phase 2
- **US2 (T010-T014)**: Depends on Phase 2, integrates with US1
- **US3 (T015-T018)**: Depends on Phase 2 + US2 (needs list endpoint)
- **US4 (T019-T021)**: Depends on Phase 2
- **Polish (T022-T025)**: Depends on all US complete

### Parallel Opportunities

- T001, T002 can run in parallel
- All test tasks (T005, T006, T010, T011, T012, T015, T016, T019) can run in parallel
- US4 can run in parallel with US1/US2/US3 after Phase 2
