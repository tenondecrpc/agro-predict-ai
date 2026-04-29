## Context

The Oracle APEX integration currently consists of:
- `models.py` - Pydantic models for connections, sync jobs, write-back requests/audits (well-defined, keep as-is)
- `repository.py` - Protocol `APEXRepository` + `InMemoryAPEXRepository` (stub, needs PostgreSQL implementation)
- `service.py` - `APEXService` with simulated `sync_data()` and `write_back()` (needs real adapter)
- `api.py` - FastAPI router (well-defined, keep as-is)

The existing spec (`specs/006-oracle-apex-integration/spec.md`) defines the requirements: read-only data ingestion, audited write-back, circuit breaker, configurable sync schedules, credential rotation.

Oracle APEX exposes data through REST APIs (ORDS - Oracle REST Data Services) and/or direct SQL. The adapter should support both patterns: REST for read-only ingestion, SQL for write-back (when explicitly approved).

## Goals / Non-Goals

**Goals:**
- Real Oracle APEX connection via `oracledb` driver
- PostgreSQL-backed repository replacing in-memory dicts
- Read-only data ingestion through Oracle APEX REST or SQL
- Audited write-back with explicit operator approval
- Circuit breaker state persisted in PostgreSQL (not just in-model)
- Alembic migration for APEX-related tables
- Tests with mock adapter and optional Oracle XE container

**Non-Goals:**
- Do not implement Oracle APEX UI or APEX application development
- Do not implement real-time CDC (Change Data Capture) from Oracle
- Do not implement Oracle wallet / mTLS authentication (phase 2)
- Do not replace the existing Pydantic models or API router

## Decisions

### 1. Use `oracledb` (thin mode) as the Oracle driver

**Decision:** Use Oracle's official `oracledb` package in thin mode (no Oracle Client required).

**Rationale:** `oracledb` thin mode connects directly to Oracle Database without requiring Oracle Instant Client libraries. This simplifies Docker images and deployment. Thin mode supports SQL execution, connection pooling, and all features needed for APEX integration.

**Alternatives considered:**
- `cx_Oracle` - deprecated, replaced by `oracledb`
- `oracledb` thick mode - requires Oracle Client, adds image size and complexity
- REST-only via ORDS - loses SQL capability needed for write-back

### 2. Adapter pattern: `OracleAPEXAdapter` protocol + implementation

**Decision:** Define an `OracleAPEXAdapter` protocol with `fetch_data()`, `write_data()`, `health_check()` methods. The implementation uses `oracledb` for SQL and `httpx` for REST.

**Rationale:** The adapter pattern isolates Oracle-specific code from the service layer. It enables mocking in tests and swapping between REST and SQL backends. The protocol matches the existing `APEXRepository` pattern.

### 3. PostgreSQL tables for APEX state

**Decision:** Store APEX connections, sync jobs, write-back audits, and quarantined records in PostgreSQL via a new Alembic migration. Circuit breaker state is stored as columns on the `apex_connections` table.

**Rationale:** PostgreSQL is the system of record. Storing APEX state there ensures consistency with the rest of the system, enables tenant-scoped RLS, and supports audit queries. The existing `InMemoryAPEXRepository` protocol maps directly to PostgreSQL tables.

### 4. Connection credentials via Vault / External Secrets

**Decision:** Oracle APEX credentials are stored as `credentials_ref` (a reference to a Vault path or External Secrets key), not as plaintext in the database. The adapter resolves the reference at runtime via the existing credentials module.

**Rationale:** The constitution mandates: "Do not store credentials in application config, environment variables committed to Git, frontend bundles, or logs." The `credentials_ref` pattern already exists in the model and aligns with this requirement.

### 5. Sync execution via ARQ worker

**Decision:** Data synchronization jobs are executed by the ARQ worker (from the `arq-worker-process` change), not by a separate scheduler. The sync schedule is stored in the connection config; a periodic ARQ job checks for due syncs.

**Rationale:** The ARQ worker already handles async job execution. Adding a periodic sync check avoids introducing a separate scheduler (Celery Beat, APScheduler, etc.). The worker can also handle retry logic and DLQ for failed syncs.

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| `oracledb` thin mode does not support all Oracle features needed | Validate against target Oracle version; thick mode is a fallback |
| Oracle XE container is large (~2GB) for integration tests | Make Oracle XE optional; default tests use mock adapter |
| Write-back SQL may conflict with APEX application triggers | Write-back uses explicit table-level operations; document trigger compatibility |
| Credential resolution fails at runtime | Circuit breaker opens; sync job fails with clear error; alert emitted |
| Large data sync exceeds memory | Use cursor-based pagination; configurable batch size |
