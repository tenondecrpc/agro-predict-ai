# Tasks: ML Model Management

---

## User Story 1 - Train and register a new model (Priority: P1)

### US1-T1: Define model management models
- **Verify**: Pydantic validation for Model, ModelValidation, ModelArtifact

### US1-T2: Implement model repository
- **Verify**: CRUD operations for models with tenant scoping

### US1-T3: Implement model registration endpoint
- **Verify**: POST /api/v1/models registers model with metadata

### US1-T4: Reject invalid model metadata
- **Verify**: Missing fields and low accuracy trigger rejection

---

## User Story 2 - Shadow-mode model validation (Priority: P2)

### US2-T1: Implement shadow mode tracking
- **Verify**: Shadow predictions stored without affecting production

### US2-T2: Implement accuracy comparison
- **Verify**: Accuracy delta calculated between shadow and active

### US2-T3: Block promotion on accuracy regression
- **Verify**: Models failing threshold cannot be promoted

---

## User Story 3 - Model versioning and rollback (Priority: P3)

### US3-T1: Implement version history
- **Verify**: GET /api/v1/models returns version list

### US3-T2: Implement rollback
- **Verify**: Previous version promoted, audit logged

---

## Verification & Archive

### V-T1: Run lint
### V-T2: Run all ML model tests
### V-T3: Archive
