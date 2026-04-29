# Tasks: Oracle APEX to Prediction Input Wiring

**Input**: Design documents from `specs/016-apex-prediction-wiring/`
**Prerequisites**: spec.md ✅, plan.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Verify `APEXService` and `FieldDataResolver` are importable and tests pass
- [ ] T002 [P] Verify APEX repository has test data for integration tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Fix the FieldDataResolver and wire it everywhere

- [ ] T003 Fix `source_id` format to include `:field_name` in `backend/src/backend/predictions/field_data_resolver.py` - change from `apex:{record_id}` to `apex:{record_id}:{field_name}`
- [ ] T004 [P] Add env var configuration for `APEX_FRESHNESS_WINDOW_SECONDS` and `APEX_SYNC_TIMEOUT_SECONDS` in `backend/src/backend/predictions/field_data_resolver.py`
- [ ] T005 [P] Add missing degradation flags (`apex_sync_timeout`, `apex_circuit_open`) in `backend/src/backend/predictions/field_data_resolver.py`

**Checkpoint**: Resolver has correct provenance format and configurable thresholds

---

## Phase 3: User Story 1 - Prediction uses APEX field data automatically (Priority: P1)

**Goal**: When input_data absent, APEX data fills prediction input. 503 when APEX unavailable.

### Tests for User Story 1

- [ ] T006 [P] [US1] Add test for prediction using APEX data when input_data absent in `backend/tests/integration/test_apex_prediction.py`
- [ ] T007 [P] [US1] Add test for 503 when APEX unavailable and input_data absent in `backend/tests/integration/test_apex_prediction.py`
- [ ] T008 [P] [US1] Add test for explicit input_data taking precedence over APEX in `backend/tests/unit/test_field_data_resolver.py`

### Implementation for User Story 1

- [ ] T009 [US1] Wire `FieldDataResolver` into the async ARQ worker path in `backend/src/backend/worker.py` (`process_prediction_run` should call `resolver.resolve()` before building `PredictionInput`)
- [ ] T010 [US1] Fix `NoInputDataError` handling in `backend/src/backend/predictions/service.py` - raise it to the API layer instead of swallowing it
- [ ] T011 [US1] Return proper 503 in `backend/src/backend/predictions/api.py` when APEX is unavailable and no manual input provided (FR-011)

**Checkpoint**: APEX data flows into both sync and async prediction paths

---

## Phase 4: User Story 2 - APEX sync triggered before prediction when data stale (Priority: P2)

**Goal**: On-demand sync when data is stale, with timeout and circuit breaker awareness

### Tests for User Story 2

- [ ] T012 [P] [US2] Add test for on-demand sync triggered when data is stale in `backend/tests/unit/test_field_data_resolver.py`
- [ ] T013 [P] [US2] Add test for sync timeout fallback with `apex_sync_timeout` flag in `backend/tests/unit/test_field_data_resolver.py`

### Implementation for User Story 2

- [ ] T014 [US2] Make `_try_on_demand_sync` async (use `asyncio.wait_for` for timeout) in `backend/src/backend/predictions/field_data_resolver.py`
- [ ] T015 [US2] Add circuit breaker state check before sync attempt - skip sync and set `apex_circuit_open` flag when circuit is open in `backend/src/backend/predictions/field_data_resolver.py`

**Checkpoint**: On-demand sync respects timeout and circuit breaker

---

## Phase 5: User Story 3 - Data provenance chain includes APEX record identity (Priority: P2)

**Goal**: Provenance entries are complete and correctly formatted

### Tests for User Story 3

- [ ] T016 [P] [US3] Add test for provenance entries including `source_id`, `ingested_at`, `validation_status`, `checksum` per feature in `backend/tests/unit/test_field_data_resolver.py`
- [ ] T017 [P] [US3] Add test for failed validation records excluded from input_data but present in provenance in `backend/tests/unit/test_field_data_resolver.py`

### Implementation for User Story 3

- [ ] T018 [US3] Generate one provenance entry per APEX-sourced feature (not one per record) in `backend/src/backend/predictions/field_data_resolver.py`
- [ ] T019 [US3] Exclude features from `feature_dict` when `validation_status != "passed"` in `backend/src/backend/predictions/field_data_resolver.py`

**Checkpoint**: Provenance chain complete per FR-007

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T020 [P] Persist `ResolvedInputData.provenance` alongside prediction output in PostgreSQL (update `PredictionService.execute()` or `worker.py` to include provenance in persisted payload) in `backend/src/backend/predictions/service.py` and `backend/src/backend/worker.py`
- [ ] T021 Run all backend tests: `uv run --project backend pytest`
- [ ] T022 Run backend lint: `uv run --project backend ruff check backend/src backend/tests`

---

## Dependencies & Execution Order

- **Phase 1 (T001-T002)**: Can start immediately
- **Phase 2 (T003-T005)**: Depends on Phase 1 - **CRITICAL** - unblocks all US
- **US1 (T006-T011)**: Depends on Phase 2
- **US2 (T012-T015)**: Depends on Phase 2
- **US3 (T016-T019)**: Depends on Phase 2
- **Polish (T020-T022)**: Depends on all US complete

### Parallel Opportunities

- T003, T004, T005 can run in parallel within Phase 2
- T006, T007, T008 can run in parallel
- T012, T013 can run in parallel
- T016, T017 can run in parallel
- US1, US2, US3 can all start in parallel after Phase 2
