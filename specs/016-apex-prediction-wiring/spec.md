# Feature Specification: Oracle APEX to Prediction Input Wiring

**Feature Branch**: `016-apex-prediction-wiring`
**Created**: 2026-04-28
**Status**: Draft
**Input**: Connect the APEX data ingestion pipeline to the prediction input path so that agronomic field data synced from Oracle APEX automatically populates PredictionInput.input_data, replacing or augmenting manual input.

## Context

`APEXService.sync_data()` in `backend/src/backend/integrations/oracle_apex/service.py` fetches field records from Oracle APEX (via `OracleSQLAdapter` or `OracleRESTAdapter`) and stores them in `APEXRepository`. However, there is no code path from this data into `PredictionInput`. The two subsystems are entirely disconnected: predictions always use the manually provided `input_data` from the HTTP request body. This spec covers: building a `FieldDataResolver` that enriches or replaces `PredictionInput.input_data` with the most recent validated APEX records for the requested tenant, crop, and region, and wiring this resolver into the prediction service before the LangGraph graph executes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prediction uses APEX field data automatically (Priority: P1)

An agronomist submits a prediction request with only `tenant_id`, `team_id`, `crop`, and `region`. The system automatically fetches the most recent validated APEX field record for that tenant/crop/region and uses it as `input_data`. The prediction response includes a data provenance entry that identifies the APEX source record, its ingestion timestamp, and its validation status.

**Why this priority**: This is the core integration value: instead of manually entering sensor readings, operators get predictions sourced from live field data. Without this wiring, APEX ingestion serves no purpose in the prediction flow.

**Independent Test**: Seed an APEX record for `tenant-alpha/corn/midwest_us` in the repository. Submit a prediction request without `input_data`. Verify the response `data_provenance` contains a `source_id` prefixed with `apex:` and the provenance checksum matches the seeded record.

**Acceptance Scenarios**:

1. **Given** a recent APEX record exists for the tenant/crop/region, **When** a prediction is submitted without `input_data`, **Then** the system uses the APEX record and includes an `apex:` provenance entry in the response.
2. **Given** the APEX record for a region is older than the configured staleness threshold, **When** a prediction is submitted, **Then** the system uses the record but sets `degradation_flags: ["apex_data_stale"]` and includes a staleness warning in the explanation artifact.
3. **Given** no APEX record exists for the requested crop/region, **When** a prediction is submitted without `input_data`, **Then** the system returns `422 Unprocessable Entity` with `"error": "no_apex_data_available"` and a suggestion to provide manual `input_data`.
4. **Given** a prediction is submitted with explicit `input_data`, **When** the resolver runs, **Then** the explicit values take precedence and APEX data is NOT used (caller override).

---

### User Story 2 - APEX sync is triggered before prediction when data is stale (Priority: P2)

When a prediction request arrives and the APEX data for the requested region is older than the configured freshness window, the system triggers an on-demand APEX sync (in the background) before executing the graph, waits up to a configurable timeout, and uses the refreshed data if the sync completes in time. If the sync times out, the system falls back to the stale data with a warning.

**Why this priority**: Predictions based on weeks-old sensor data are unreliable. Triggering a sync on-demand ensures the model receives the freshest available data for time-sensitive agricultural decisions.

**Independent Test**: Set the APEX staleness threshold to 1 minute. Seed a 2-minute-old APEX record. Submit a prediction. Verify an APEX sync is triggered and the prediction uses the refreshed record (or the stale record with warning if the mock sync times out).

**Acceptance Scenarios**:

1. **Given** APEX data is stale (older than `APEX_FRESHNESS_WINDOW_SECONDS`), **When** a prediction is submitted, **Then** an async APEX sync is triggered and the system waits up to `APEX_SYNC_TIMEOUT_SECONDS` for fresh data.
2. **Given** the on-demand sync completes before the timeout, **When** the graph executes, **Then** it uses the freshly synced data with no staleness degradation flag.
3. **Given** the on-demand sync times out, **When** the graph executes, **Then** it uses the last available data and sets `degradation_flags: ["apex_sync_timeout"]`.
4. **Given** the APEX adapter circuit breaker is open, **When** a prediction is submitted with stale data, **Then** the sync is skipped, the stale data is used, and `degradation_flags: ["apex_circuit_open"]` is set.

---

### User Story 3 - Data provenance chain includes APEX record identity (Priority: P2)

Every prediction that uses APEX data includes a provenance entry for each APEX-sourced feature. The entry records the APEX record ID, the field identifier, the ingestion timestamp, the validation status, and a checksum of the raw value. This provenance is attached to the `PredictionOutput` and persisted in PostgreSQL alongside the prediction.

**Why this priority**: The constitution mandates complete data provenance chains. APEX-sourced predictions must be auditable back to their source records to satisfy the Tier 1 non-negotiable on data-driven decisions.

**Independent Test**: Run a prediction with APEX data. Query the `predictions` table and verify the JSONB `payload` contains a `data_provenance` array where at least one entry has `source_id` starting with `apex:`, a non-null `checksum`, and `validation_status: "passed"`.

**Acceptance Scenarios**:

1. **Given** a prediction using APEX data, **When** the prediction is persisted, **Then** `data_provenance` contains one entry per APEX feature with `source_id`, `ingested_at`, `validation_status`, and `checksum`.
2. **Given** an APEX record that failed validation, **When** the `FieldDataResolver` processes it, **Then** the feature is excluded from `input_data`, its provenance entry shows `validation_status: "failed"`, and the gap is flagged in `uncertainty_factors`.

---

### Edge Cases

- What happens when APEX data is available for some features but not all required by the model?
- How does the system behave when APEX returns multiple records for the same region (e.g., multiple sensor nodes)?
- What happens when the APEX adapter is in dev mode (returning sample data) but the region has no sample entry?
- How does tenant isolation apply when the same region has records from multiple tenants?
- What happens when APEX sync completes during the graph execution after `data_analyst` has already consumed the stale data?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A `FieldDataResolver` component MUST be injected into the prediction service and invoked before the LangGraph graph starts.
- **FR-002**: `FieldDataResolver.resolve()` MUST return a `ResolvedInputData` object containing the feature dict, provenance entries, and a staleness flag.
- **FR-003**: When `input_data` is absent from the request, `FieldDataResolver` MUST query `APEXRepository` for the most recent validated record matching `tenant_id`, `crop`, and `region`.
- **FR-004**: When `input_data` is present in the request, `FieldDataResolver` MUST pass it through unchanged and MUST NOT query APEX.
- **FR-005**: Staleness is determined by comparing the record's `ingested_at` timestamp against `APEX_FRESHNESS_WINDOW_SECONDS` (default: 3600).
- **FR-006**: When data is stale, an on-demand sync MUST be triggered asynchronously and awaited up to `APEX_SYNC_TIMEOUT_SECONDS` (default: 10).
- **FR-007**: Each APEX-sourced feature MUST produce a provenance entry with `source_id: "apex:{record_id}:{field_name}"`, `ingested_at`, `validation_status`, and `checksum` (SHA-256 of the raw value, first 16 hex chars).
- **FR-008**: Records from a different tenant MUST NOT be used for predictions from another tenant (strict tenant isolation in all APEX queries).
- **FR-009**: When multiple APEX records exist for the same region, the resolver MUST select the most recently ingested validated record.
- **FR-010**: The APEX integration MUST remain read-only. `FieldDataResolver` MUST NOT write to Oracle APEX.
- **FR-011**: If APEX is unavailable (circuit open) and `input_data` is absent, the endpoint MUST return `503` rather than proceeding with no data.

### Key Entities

- **ResolvedInputData**: Dataclass. Fields: `feature_dict` (the final input for the model), `provenance` (list of provenance entries), `is_stale` (bool), `stale_age_seconds` (int), `source` (enum: `apex` / `manual` / `hybrid`).
- **APEXFieldRecord**: Repository model. Fields: `record_id`, `tenant_id`, `crop`, `region`, `field_name`, `raw_value`, `validated_value`, `validation_status`, `ingested_at`, `checksum`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of predictions using APEX data include at least one `apex:`-prefixed provenance entry in the persisted output.
- **SC-002**: Tenant isolation: zero cross-tenant APEX record accesses across 10,000 randomly generated prediction requests in the integration test suite.
- **SC-003**: On-demand sync completes within `APEX_SYNC_TIMEOUT_SECONDS` in 90% of cases under normal APEX connectivity.
- **SC-004**: Predictions submitted without `input_data` succeed (return 2xx) when a valid APEX record exists, and fail with `422` when no APEX record exists.
- **SC-005**: Zero cases of a prediction using unvalidated (`validation_status != "passed"`) APEX data without a corresponding `uncertainty_factors` entry.
