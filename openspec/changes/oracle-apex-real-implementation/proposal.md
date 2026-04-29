## Why

The Oracle APEX integration is currently a stub: `InMemoryAPEXRepository` uses Python dicts, `APEXService.sync_data()` simulates data fetch with `sample_data`, and `write_back()` simulates sending to APEX without any network call. No Oracle driver is installed. This blocks the enterprise data ingestion path required for the prediction pipeline to operate on real agricultural and logistics data.

## What Changes

- Add `oracledb` (Oracle Python driver) as a backend dependency
- Implement `PostgresAPEXRepository` that persists connections, sync jobs, and write-back audits in PostgreSQL
- Implement `OracleAPEXAdapter` that makes real HTTP/SQL calls to Oracle APEX REST endpoints
- Update `APEXService` to use the real adapter for `sync_data()` and `write_back()`
- Add Alembic migration for Oracle APEX tables (connections, sync_jobs, writeback_audits, quarantined_records)
- Wire the APEX router in `app.py` when a real repository is configured
- Add tests: unit tests with mock Oracle adapter, integration tests with test Oracle container

## Capabilities

### New Capabilities
- `oracle-apex-adapter`: Real Oracle APEX HTTP/SQL adapter with connection pooling, query execution, and write-back
- `oracle-apex-persistence`: PostgreSQL-backed repository for APEX connections, sync jobs, write-back audits, quarantined records

### Modified Capabilities
- `oracle-apex-integration`: Replace in-memory repository with PostgreSQL-backed repository; replace simulated service with real adapter calls

## Impact

- `backend/pyproject.toml` - add `oracledb` dependency
- `backend/src/backend/integrations/oracle_apex/repository.py` - new `PostgresAPEXRepository`
- `backend/src/backend/integrations/oracle_apex/adapter.py` - new Oracle APEX adapter
- `backend/src/backend/integrations/oracle_apex/service.py` - update to use real adapter
- `backend/alembic/versions/` - new migration for APEX tables
- `backend/src/backend/app.py` - wire real APEX service when configured
- `docker-compose.yml` - optional Oracle XE container for integration tests
- `backend/tests/` - new test files for adapter and PostgreSQL repository
