# Tasks: Prediction Pipeline

Organized by user story. Each task is test-first (TDD).

---

## User Story 1 - Execute end-to-end prediction (Priority: P1)

### US1-T1: Define prediction data models
- **Type**: Implementation + Unit Test
- **Verify**: `test_prediction_models.py` passes with Pydantic model validation for `PredictionInput`, `PredictionOutput`, `PredictionState`, `AgentExecutionRecord`, `ExplanationArtifactModel`
- **Acceptance**: Models enforce required fields, correct types, and JSON serialization

### US1-T2: Define PredictionRepository contract + in-memory impl
- **Type**: Implementation + Unit Test
- **Verify**: `test_prediction_repository.py` passes - create, read, list predictions with tenant scoping
- **Acceptance**: Protocol defines `save`, `get_by_id`, `list_by_tenant`. In-memory implementation passes all tests.

### US1-T3: Implement data_analyst agent
- **Type**: Implementation + Unit Test
- **Verify**: `test_data_analyst.py` passes - validates input data, computes input_data_hash, flags stale/incomplete data
- **Acceptance**: Agent returns validated data or explicit failure signal with `DataQualityError`. Stale data triggers uncertainty flag.

### US1-T4: Implement ml_executor agent
- **Type**: Implementation + Unit Test
- **Verify**: `test_ml_executor.py` passes - runs model, produces output + confidence interval
- **Acceptance**: Agent loads active model by version, produces numeric prediction and confidence tuple. On model failure, attempts cached-model fallback.

### US1-T5: Implement recommendation_engine agent
- **Type**: Implementation + Unit Test
- **Verify**: `test_recommendation_engine.py` passes - generates actionable recommendation text
- **Acceptance**: Agent transforms model output into human-readable recommendation with context.

### US1-T6: Implement explainability agent
- **Type**: Implementation + Unit Test
- **Verify**: `test_explainability.py` passes - produces feature importance scores and provenance chain
- **Acceptance**: Agent returns feature_scores dict, data_sources_used list, and human_readable_summary.

### US1-T7: Implement reviewer agent
- **Type**: Implementation + Unit Test
- **Verify**: `test_reviewer.py` passes - validates output completeness and policy compliance
- **Acceptance**: Agent approves or rejects prediction. Rejection includes explicit reason and routes to escalation sink.

### US1-T8: Build prediction LangGraph StateGraph
- **Type**: Implementation + Integration Test
- **Verify**: `test_prediction_graph.py` passes - full graph invocation with mocked agents
- **Acceptance**: Graph traverses data_analyst -> ml_executor -> recommendation_engine -> explainability -> reviewer in sequence. Conditional routing on failure to escalation.

### US1-T9: Build PredictionService orchestration layer
- **Type**: Implementation + Integration Test
- **Verify**: `test_prediction_service.py` passes - service.execute() returns completed PredictionOutput
- **Acceptance**: Service creates prediction record, invokes graph, persists result, and returns with provenance.

### US1-T10: Add FastAPI endpoint POST /api/v1/predictions
- **Type**: Implementation + Integration Test
- **Verify**: `test_predictions_api.py` passes - HTTP request returns 200 with complete prediction response
- **Acceptance**: Endpoint accepts JSON body, validates input, calls service, returns PredictionOutput. Returns 422 on invalid input. Returns 503 on pipeline timeout.

---

## User Story 2 - Graceful degradation on agent failure (Priority: P2)

### US2-T1: Test ml_executor failure with cached-model fallback
- **Type**: Unit Test + Implementation
- **Verify**: When `ml_executor` raises ModelUnavailableError, graph routes to fallback path and returns prediction with `staleness_warning=True` and degraded confidence
- **Acceptance**: Cached-model fallback activates within graph execution. Response metadata contains `degradation_flags: ["cached_model_fallback"]`.

### US2-T2: Test explainability agent failure
- **Type**: Unit Test + Implementation
- **Verify**: When `explainability` fails, graph continues and returns prediction without explanation artifacts but with `explainability_missing: true` in metadata
- **Acceptance**: No crash. Prediction output is valid. Metadata explicitly flags missing explainability.

### US2-T3: Test timeout mid-pipeline
- **Type**: Integration Test + Implementation
- **Verify**: Graph timeout triggers graceful termination with partial results and `timeout_exceeded: true`
- **Acceptance**: Partial prediction record persisted. Escalation reason set to `TIMEOUT_EXCEEDED`. No data corruption.

### US2-T4: Test escalation sink routing on unrecoverable failure
- **Type**: Integration Test + Implementation
- **Verify**: All failure paths route to a registered escalation sink with explicit `EscalationReason`
- **Acceptance**: Escalation sink receives `prediction_id`, `failed_agent`, `reason`, and `partial_state`.

---

## User Story 3 - Prediction with explainability artifacts (Priority: P3)

### US3-T1: Test explanation artifact completeness
- **Type**: Unit Test + Implementation
- **Verify**: Every successful prediction includes `feature_importance`, `data_sources_used`, `confidence_level`, `uncertainty_factors`, `human_readable_summary`
- **Acceptance**: All fields present and non-empty in successful predictions.

### US3-T2: Test low-confidence highlighting
- **Type**: Unit Test + Implementation
- **Verify**: When confidence < 0.7, explanation artifact highlights top 3 uncertainty factors
- **Acceptance**: `uncertainty_factors` list ordered by contribution magnitude. Human-readable summary includes warning language.

### US3-T3: Test provenance chain integrity
- **Type**: Integration Test + Implementation
- **Verify**: Data provenance chain includes all data sources with timestamps and validation status
- **Acceptance**: Provenance entries include `source_id`, `ingested_at`, `validation_status`, `checksum`.

---

## Verification & Archive

### V-T1: Run lint
- Command: `uv run --project backend ruff check backend/src backend/tests`
- Gate: Zero errors

### V-T2: Run all prediction tests
- Command: `uv run --project backend pytest backend/tests/unit/predictions/ backend/tests/integration/test_predictions_api.py -v`
- Gate: 100% pass rate

### V-T3: Constitution Check
- Verify: All Tier 1 non-negotiables preserved (data quality gate before prediction, provenance chains, graceful degradation, agent communication via LangGraph state only)

### V-T4: Archive
- Run `.specify/scripts/bash/archive-change.sh` (or manual archive steps)
- Update spec status to Implemented
