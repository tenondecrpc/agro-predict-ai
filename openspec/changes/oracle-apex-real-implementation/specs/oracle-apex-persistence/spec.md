## ADDED Requirements

### Requirement: PostgresAPEXRepository
The system SHALL implement `PostgresAPEXRepository` that persists Oracle APEX connections, sync jobs, write-back audits, and quarantined records in PostgreSQL.

#### Scenario: Repository saves and retrieves connections
- **WHEN** a connection is saved via `save_connection()`
- **THEN** it is stored in the `apex_connections` table and retrievable via `get_connection()`

#### Scenario: Repository saves and retrieves sync jobs
- **WHEN** a sync job is saved via `save_sync_job()`
- **THEN** it is stored in the `apex_sync_jobs` table and retrievable via `get_sync_job()`

#### Scenario: Repository saves and retrieves write-back audits
- **WHEN** a write-back audit is saved via `save_writeback_audit()`
- **THEN** it is stored in the `apex_writeback_audits` table and retrievable via `get_writeback_audit()`

#### Scenario: Repository lists audits by tenant
- **WHEN** `list_writeback_audits(tenant_id)` is called
- **THEN** only audits for the specified tenant are returned (RLS-enforced)

### Requirement: Alembic migration for APEX tables
The system SHALL include an Alembic migration that creates the Oracle APEX tables with proper constraints and RLS policies.

#### Scenario: Migration creates apex_connections table
- **WHEN** the migration is applied
- **THEN** the `apex_connections` table is created with columns: id, tenant_id, endpoint, credentials_ref, sync_schedule, status, circuit_breaker_state, failure_count, last_failure_at, created_at, updated_at

#### Scenario: Migration creates apex_sync_jobs table
- **WHEN** the migration is applied
- **THEN** the `apex_sync_jobs` table is created with columns: id, tenant_id, connection_id, start_time, end_time, records_ingested, records_validated, records_quarantined, status, error_message

#### Scenario: Migration creates apex_writeback_audits table
- **WHEN** the migration is applied
- **THEN** the `apex_writeback_audits` table is created with columns: id, tenant_id, prediction_id, oracle_apex_table, data_written (JSONB), approved_by, approved_at, status, error_message, created_at

#### Scenario: Migration creates apex_quarantined_records table
- **WHEN** the migration is applied
- **THEN** the `apex_quarantined_records` table is created with columns: id, tenant_id, sync_job_id, raw_data (JSONB), rejection_reason, created_at

#### Scenario: Migration applies RLS policies
- **WHEN** the migration is applied
- **THEN** Row Level Security policies are created on all APEX tables scoped to tenant_id

#### Scenario: Migration is reversible
- **WHEN** the migration is rolled back
- **THEN** all APEX tables are dropped cleanly

### Requirement: Circuit breaker state persisted in PostgreSQL
The system SHALL store circuit breaker state (state, failure_count, last_failure_at) in the `apex_connections` table, not just in memory.

#### Scenario: Circuit breaker state updated on failure
- **WHEN** a sync job fails
- **THEN** the connection's `failure_count` is incremented and `circuit_breaker_state` is updated in PostgreSQL

#### Scenario: Circuit breaker state updated on success
- **WHEN** a sync job succeeds after being in HALF_OPEN state
- **THEN** the connection's `circuit_breaker_state` is set to CLOSED and `failure_count` is reset to 0 in PostgreSQL

#### Scenario: Circuit breaker opens after threshold
- **WHEN** failure_count reaches 5
- **THEN** `circuit_breaker_state` is set to OPEN in PostgreSQL

### Requirement: APEX service uses real adapter
The system SHALL update `APEXService.sync_data()` and `APEXService.write_back()` to use the real `OracleAPEXAdapter` instead of simulating operations.

#### Scenario: sync_data fetches real data from Oracle
- **WHEN** `sync_data()` is called with a valid connection_id
- **THEN** the adapter fetches data from Oracle APEX and returns actual records

#### Scenario: write_back sends real data to Oracle
- **WHEN** `write_back()` is called with an approved request
- **THEN** the adapter writes data to the specified Oracle APEX table

#### Scenario: sync_data respects circuit breaker
- **WHEN** `sync_data()` is called and the circuit breaker is OPEN
- **THEN** the job fails immediately without attempting a connection

### Requirement: APEX router wired when real repository configured
The system SHALL include the APEX router in the FastAPI app when a real `PostgresAPEXRepository` is configured.

#### Scenario: Router active with real repository
- **WHEN** the app is created with a configured `PostgresAPEXRepository`
- **THEN** the `/api/v1/apex` routes are registered and functional

#### Scenario: Router inactive without real repository
- **WHEN** the app is created without a configured repository (default)
- **THEN** the `/api/v1/apex` routes are not registered
