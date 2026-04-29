## 1. Oracle APEX adapter

- [ ] 1.1 Add `oracledb` and `httpx` to `backend/pyproject.toml` dependencies
- [ ] 1.2 Create `OracleAPEXAdapter` protocol in `backend/src/backend/integrations/oracle_apex/adapter.py`
- [ ] 1.3 Implement `OracleAPEXAdapter` with `oracledb` thin mode connection pool
- [ ] 1.4 Implement `fetch_data()` with SQL query execution and cursor-based pagination
- [ ] 1.5 Implement `fetch_data()` with REST endpoint support via `httpx`
- [ ] 1.6 Implement `write_data()` for SQL INSERT/UPDATE operations
- [ ] 1.7 Implement `health_check()` with `SELECT 1 FROM DUAL`
- [ ] 1.8 Implement credential resolution from `credentials_ref` via existing credentials module

## 2. PostgreSQL repository

- [ ] 2.1 Create `PostgresAPEXRepository` implementing `APEXRepository` protocol
- [ ] 2.2 Implement `save_connection()` and `get_connection()` with SQLAlchemy
- [ ] 2.3 Implement `save_sync_job()` and `get_sync_job()` with SQLAlchemy
- [ ] 2.4 Implement `save_writeback_audit()`, `get_writeback_audit()`, `list_writeback_audits()` with SQLAlchemy
- [ ] 2.5 Add circuit breaker state persistence (update connection record on failure/success)
- [ ] 2.6 Add tenant-scoped RLS enforcement in all repository queries

## 3. Alembic migration

- [ ] 3.1 Create Alembic migration for `apex_connections` table with RLS policies
- [ ] 3.2 Create Alembic migration for `apex_sync_jobs` table with RLS policies
- [ ] 3.3 Create Alembic migration for `apex_writeback_audits` table with RLS policies
- [ ] 3.4 Create Alembic migration for `apex_quarantined_records` table with RLS policies
- [ ] 3.5 Verify migration is reversible (downgrade drops all tables cleanly)

## 4. Service layer update

- [ ] 4.1 Update `APEXService` to accept `OracleAPEXAdapter` as constructor parameter
- [ ] 4.2 Update `sync_data()` to use real adapter for data fetch
- [ ] 4.3 Update `write_back()` to use real adapter for data write
- [ ] 4.4 Wire APEX router in `app.py` when real repository is configured

## 5. Tests

- [ ] 5.1 Write unit tests for `OracleAPEXAdapter` with mock `oracledb` connection
- [ ] 5.2 Write unit tests for `PostgresAPEXRepository` with ephemeral PostgreSQL
- [ ] 5.3 Write unit tests for updated `APEXService` with mock adapter
- [ ] 5.4 Write integration test: full sync flow (adapter -> service -> repository -> PostgreSQL)
- [ ] 5.5 Write integration test: write-back flow with approval and audit

## 6. Docker Compose (optional)

- [ ] 6.1 Add optional Oracle XE service to `docker-compose.yml` (disabled by default)
- [ ] 6.2 Add `make apex-up` target to start Oracle XE for integration tests

## 7. Documentation

- [ ] 7.1 Update README.md with Oracle APEX configuration instructions
- [ ] 7.2 Update README.md roadmap table for spec 006-oracle-apex-integration status
