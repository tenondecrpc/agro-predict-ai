# Feature Specification: Real ML Model with Adapter Pattern

**Feature Branch**: `015-real-ml-model`
**Created**: 2026-04-28
**Status**: Draft
**Input**: Replace the hardcoded linear formula in ml_executor with a real trained scikit-learn model (RandomForestRegressor) serialized with joblib, loaded at startup via the adapter pattern that already exists, and versioned in the model registry.

## Context

`ml_executor._run_model()` in `backend/src/backend/predictions/agents/ml_executor.py` computes yield as `3.0 + soil*10 + temp*0.15 + rain*0.03`. The `MODEL_REGISTRY` is a static dict with one hardcoded entry. There is no scikit-learn fit, no model file on disk, no ONNX artifact, and no real training pipeline. The adapter interface exists but wraps a formula. This spec covers: training a baseline `RandomForestRegressor` on synthetic agronomic data, serializing it with `joblib`, loading it at startup through the adapter, versioning the artifact in the model registry PostgreSQL table, and exposing accuracy metrics and drift checks.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - ml_executor loads and runs a real scikit-learn model (Priority: P1)

When the backend starts, the ML adapter loads the model artifact from disk (or object storage in production). When `ml_executor` executes, it passes the validated feature vector through `model.predict()` and `model.predict_proba()` (or equivalent uncertainty estimation via bootstrap), and returns a yield prediction with a real confidence interval derived from the ensemble variance.

**Why this priority**: The entire prediction pipeline has no real ML - all current outputs are deterministic formulas. A real model is required for agronomic credibility and to validate the full pipeline under realistic conditions.

**Independent Test**: Load the serialized model in isolation, run `predict([[0.35, 22.5, 45.0]])`, and verify the output is a float in a plausible agronomic range (e.g., 3-20 tons/hectare for corn). Verify confidence interval lower < prediction < upper.

**Acceptance Scenarios**:

1. **Given** the model artifact exists at the configured path, **When** the backend starts, **Then** the adapter loads the model without error and `MODEL_REGISTRY` reports the model as `active` with version, training date, and dataset hash.
2. **Given** valid feature inputs, **When** `ml_executor` runs, **Then** it returns a yield prediction from `model.predict()`, a confidence interval from ensemble variance, and feature importance from `model.feature_importances_`.
3. **Given** the model artifact is missing at startup, **When** the application starts with `MODEL_FALLBACK_ENABLED=true`, **Then** it logs a warning and activates the formula fallback, setting `degradation_flags: ["model_file_missing"]`.
4. **Given** an input feature vector with values outside the training distribution, **When** `ml_executor` runs, **Then** it flags the out-of-distribution inputs in `uncertainty_factors` and lowers the reported confidence.

---

### User Story 2 - Model is versioned in the registry with metadata (Priority: P2)

Each model artifact is registered in the PostgreSQL `model_registry` table with version string, training date, dataset hash, accuracy metrics (MAE, RMSE, R2), and feature schema. The active model version is selected at runtime from the registry. An operator can promote a new model version to `active` via the admin API, triggering shadow-mode validation before full activation.

**Why this priority**: The constitution requires model artifacts to be versioned with metadata. Unversioned models cannot be audited, rolled back, or compared.

**Independent Test**: Register a model version via `POST /api/v1/models`, verify the record appears in the `model_registry` table, promote it to `shadow`, verify it runs alongside the active model on a test prediction, then promote to `active` and verify it is used for subsequent predictions.

**Acceptance Scenarios**:

1. **Given** a new model artifact is uploaded, **When** `POST /api/v1/models` is called with version metadata, **Then** the record is inserted into `model_registry` with status `staged`.
2. **Given** a staged model, **When** shadow-mode is activated, **Then** both the active and shadow models run on every prediction and their outputs are logged for comparison without affecting the returned result.
3. **Given** shadow-mode validation passes accuracy thresholds, **When** an operator promotes the model, **Then** the new version becomes `active` and the old version is archived.
4. **Given** an active model's accuracy regresses below the configured threshold, **When** the regression check runs, **Then** the system emits a `model_accuracy_regression` alert and blocks automatic promotion of new shadow models.

---

### User Story 3 - Training pipeline produces a versioned artifact (Priority: P3)

A developer runs the training script against the agronomic dataset (synthetic or real). The script validates the dataset, trains the `RandomForestRegressor`, evaluates on a held-out test set, serializes the model with `joblib`, records the dataset hash and accuracy metrics, and outputs an artifact ready for registration in the registry.

**Why this priority**: Without a reproducible training pipeline, model artifacts are black boxes. The training script provides a verifiable chain from dataset to deployed artifact.

**Independent Test**: Run the training script against the synthetic dataset included in the repository. Verify it produces a `.joblib` file, a `model_metadata.json` with version, dataset hash, MAE, RMSE, and R2, and that the script exits 0.

**Acceptance Scenarios**:

1. **Given** the synthetic training dataset, **When** the training script runs, **Then** it produces a `.joblib` artifact and `model_metadata.json` with all required fields.
2. **Given** a dataset that fails validation (missing required columns), **When** the training script runs, **Then** it exits with a non-zero code and a clear error message identifying the missing columns.
3. **Given** a trained model with R2 below the minimum threshold (e.g., 0.60), **When** the training script evaluates, **Then** it rejects the artifact and does not write the `.joblib` file.

---

### Edge Cases

- What happens when the model is loaded but the feature schema of incoming data does not match the trained feature set?
- How does the system handle a model that produces negative yield predictions?
- What happens when the model file is corrupted (truncated joblib)?
- How does shadow-mode behave when the active and shadow models disagree by more than 30%?
- What happens in air-gapped deployments where the model artifact must be bundled in the container image?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `ml_executor` MUST load its model through the `MLModelAdapter` interface, not by calling any formula directly.
- **FR-002**: The adapter MUST call `model.predict()` for point estimates and compute confidence intervals using the ensemble's per-tree predictions (variance method for `RandomForestRegressor`).
- **FR-003**: The adapter MUST return `feature_importances_` from the fitted model as the `feature_importance` dict.
- **FR-004**: Model artifacts MUST be serialized with `joblib` and versioned with a filename pattern `{crop}_{model_type}_v{version}_{dataset_hash[:8]}.joblib`.
- **FR-005**: A `model_registry` PostgreSQL table MUST store version, training date, dataset hash, accuracy metrics (MAE, RMSE, R2), feature schema, status (`staged`/`shadow`/`active`/`archived`), and artifact path.
- **FR-006**: The active model MUST be selected at startup by querying `model_registry` for `status = 'active'` and `crop = X`. The result MUST be cached in memory and invalidated on registry change.
- **FR-007**: Shadow-mode MUST run both active and shadow models on every prediction and persist both outputs to a `shadow_comparisons` table without affecting the caller response.
- **FR-008**: The training script MUST validate the dataset schema before training.
- **FR-009**: The training script MUST reject models with R2 below a configurable `MIN_MODEL_R2` threshold (default: 0.60).
- **FR-010**: The adapter MUST detect out-of-distribution inputs by comparing feature values against training-set quantiles (1st/99th percentile) stored in model metadata, and flag them in `uncertainty_factors`.
- **FR-011**: If the model artifact is missing and `MODEL_FALLBACK_ENABLED=true`, the adapter MUST activate the formula fallback and set `degradation_flags: ["model_file_missing"]`.
- **FR-012**: Model artifact path MUST be configurable via `ML_MODEL_PATH` environment variable (supports both local filesystem and mounted volumes for Kubernetes).

### Key Entities

- **ModelArtifact**: Serialized scikit-learn pipeline (preprocessor + RandomForestRegressor) stored as `.joblib` file.
- **ModelRegistryRecord**: PostgreSQL row. Fields: `model_id`, `crop`, `model_type`, `version`, `artifact_path`, `dataset_hash`, `trained_at`, `mae`, `rmse`, `r2`, `feature_schema` (JSONB), `status`, `promoted_at`, `promoted_by`.
- **ShadowComparison**: PostgreSQL row. Fields: `comparison_id`, `prediction_id`, `active_version`, `shadow_version`, `active_output`, `shadow_output`, `delta_pct`, `recorded_at`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `ml_executor` returns predictions from a loaded `.joblib` model artifact (verifiable by removing the formula code path entirely).
- **SC-002**: The baseline `RandomForestRegressor` achieves R2 >= 0.70 on the synthetic held-out test set.
- **SC-003**: Feature importance values sum to 1.0 (±0.001) for every prediction.
- **SC-004**: Shadow-mode records 100% of prediction pairs when enabled.
- **SC-005**: Out-of-distribution detection flags at least 95% of inputs with feature values outside the 1st/99th percentile range of training data (verified on a synthetic OOD test set).
- **SC-006**: Model loading at startup completes in under 2 seconds for artifacts up to 500 MB.
