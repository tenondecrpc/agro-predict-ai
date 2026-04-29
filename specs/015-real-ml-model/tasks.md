# Tasks: Real ML Model with Adapter Pattern

**Input**: Design documents from `specs/015-real-ml-model/`
**Prerequisites**: spec.md ✅, plan.md ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Verify `model_registry` migration exists and includes all required columns
- [ ] T002 [P] Verify `shadow_comparisons` table exists in the migration

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create PostgreSQL-backed model repository

- [ ] T003 Add `model_registry` SQLAlchemy Table definition in `backend/src/backend/predictions/models/schema.py`
- [ ] T004 [P] Add `shadow_comparisons` SQLAlchemy Table definition in `backend/src/backend/predictions/models/schema.py`
- [ ] T005 Create `PostgresModelRepository` implementing the `ModelRepository` interface in `backend/src/backend/ml/models/repository.py` (or new file `backend/src/backend/ml/models/pg_repository.py`)

**Checkpoint**: PostgreSQL model repository ready to replace InMemory

---

## Phase 3: User Story 2 - Model versioned in registry with metadata (Priority: P2)

**Goal**: Active model selected at startup from PostgreSQL, shadow-mode promotion works

### Tests for User Story 2

- [ ] T006 [P] [US2] Add test for PostgresModelRepository CRUD (register, get_active, promote) in `backend/tests/integration/test_model_repo.py`
- [ ] T007 [P] [US2] Add test for shadow-mode promotion flow (staged -> shadow -> active) in `backend/tests/integration/test_model_repo.py`

### Implementation for User Story 2

- [ ] T008 [US2] Wire `PostgresModelRepository` into the app startup in `backend/src/backend/app.py` so `MLExecutorAgent` loads the active model from PostgreSQL
- [ ] T009 [US2] Implement `can_promote()` in `backend/src/backend/ml/control_plane/service.py` - check accuracy thresholds, existing shadow validations, regression alerts
- [ ] T010 [US2] Wire `ModelService.promote_to_active()` to use PostgreSQL repository instead of InMemory in `backend/src/backend/ml/control_plane/service.py`

**Checkpoint**: Model registry backed by PostgreSQL, promotion flow working

---

## Phase 4: User Story 1 - Shadow-mode dual execution (Priority: P1)

**Goal**: Both active and shadow models run on every prediction, outputs compared and logged

### Tests for User Story 1

- [ ] T011 [P] [US1] Add test for shadow-mode dual execution - verify both model outputs are computed in `backend/tests/unit/test_shadow_mode.py`
- [ ] T012 [P] [US1] Add test for shadow comparison record written when shadow model active in `backend/tests/unit/test_shadow_mode.py`

### Implementation for User Story 1

- [ ] T013 [US1] In `backend/src/backend/predictions/agents/ml_executor.py`, add `_run_shadow_model()` method that loads the shadow model from registry and runs it alongside the active model
- [ ] T014 [US1] Create `ShadowComparisonRepository` in `backend/src/backend/ml/shadow_comparisons/repository.py` to persist comparison records to PostgreSQL
- [ ] T015 [US1] Wire shadow dual-execution into `MLExecutorAgent._run_model()` - when a shadow model exists, run both, persist comparison, return active output to caller

**Checkpoint**: Shadow models execute alongside active, comparisons persisted

---

## Phase 5: User Story 3 - Training pipeline (Priority: P3)

**Goal**: Training script is already complete - verify and document

### Validation for User Story 3

- [ ] T016 [US3] Verify training script executes successfully: `python backend/scripts/train_model.py`
- [ ] T017 [US3] Verify trained model artifact can be loaded by `ScikitLearnAdapter` and predictions match expected range

**Checkpoint**: Training pipeline verified

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T018 [P] Update `MLExecutorAgent.__init__()` to accept `PostgresModelRepository` for dynamic model selection in `backend/src/backend/predictions/agents/ml_executor.py`
- [ ] T019 [P] Add env var `ML_MODEL_PATH` fallback to PostgreSQL-stored artifact path in `backend/src/backend/ml/adapter.py`
- [ ] T020 Run all backend tests: `uv run --project backend pytest`
- [ ] T021 Run backend lint: `uv run --project backend ruff check backend/src backend/tests`

---

## Dependencies & Execution Order

- **Phase 1 (T001-T002)**: Can start immediately
- **Phase 2 (T003-T005)**: Depends on Phase 1 - **CRITICAL** - unblocks all US
- **US2 (T006-T010)**: Depends on Phase 2
- **US1 (T011-T015)**: Depends on Phase 2 + US2 (needs registry for shadow models)
- **US3 (T016-T017)**: Can run anytime (independent of Phase 2)
- **Polish (T018-T021)**: Depends on US1+US2 complete

### Parallel Opportunities

- T003, T004 can run in parallel
- T006, T007 can run in parallel
- T011, T012 can run in parallel
- US3 (T016-T017) can run in parallel with Phase 2+US2
