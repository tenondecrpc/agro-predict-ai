# Tasks: Data Ingestion Layer

Organized by user story. Each task is test-first (TDD).

---

## User Story 1 - Ingest agricultural data via API (Priority: P1)

### US1-T1: Define data ingestion models
- **Type**: Implementation + Unit Test
- **Verify**: `test_models.py` passes for DataRecord, DataSource, QualityGate
- **Acceptance**: Pydantic models enforce schema, types, and validation

### US1-T2: Build schema registry and validator
- **Type**: Implementation + Unit Test
- **Verify**: `test_schemas.py` passes - validate payloads against registered schemas
- **Acceptance**: Missing fields return 400, unknown fields rejected, type coercion works

### US1-T3: Implement single-record ingestion endpoint
- **Type**: Implementation + Integration Test
- **Verify**: `test_data_api.py` passes for POST /api/v1/data/ingest
- **Acceptance**: Valid data returns 201 with provenance_id, invalid returns 400 with details

### US1-T4: Implement batch ingestion
- **Type**: Implementation + Integration Test
- **Verify**: Batch POST accepts array, validates each record, returns summary
- **Acceptance**: All-or-nothing transactional, partial failures reported

---

## User Story 2 - Data quality gate enforcement (Priority: P2)

### US2-T1: Implement completeness gate
- **Type**: Unit Test + Implementation
- **Verify**: Records with missing required fields fail gate
- **Acceptance**: Missing fields identified, record quarantined

### US2-T2: Implement freshness gate
- **Type**: Unit Test + Implementation
- **Verify**: Records older than threshold fail gate
- **Acceptance**: Stale data quarantined with staleness alert

### US2-T3: Implement range validation gate
- **Type**: Unit Test + Implementation
- **Verify**: Values outside configured ranges flagged
- **Acceptance**: Range violations stored with quality warning

### US2-T4: Implement cross-source consistency gate
- **Type**: Unit Test + Implementation
- **Verify**: Contradictory data from different sources flagged
- **Acceptance**: Contradictions logged, data quarantined

### US2-T5: Quality dashboard endpoint
- **Type**: Integration Test + Implementation
- **Verify**: GET /api/v1/data/quality returns current gate status
- **Acceptance**: Returns pass/fail counts per gate, quarantine size

---

## User Story 3 - Data provenance tracking (Priority: P3)

### US3-T1: Provenance ID assignment
- **Type**: Unit Test + Implementation
- **Verify**: Every record gets unique provenance_id
- **Acceptance**: ID is deterministic from source+timestamp+hash

### US3-T2: Provenance chain in predictions
- **Type**: Integration Test + Implementation
- **Verify**: Prediction provenance references ingested data sources
- **Acceptance**: Prediction output includes source_id, ingestion_timestamp, quality_status

---

## Verification & Archive

### V-T1: Run lint
### V-T2: Run all data ingestion tests
### V-T3: Constitution Check
### V-T4: Archive
