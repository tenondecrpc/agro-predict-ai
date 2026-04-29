# Oracle APEX Integration

## Overview

AgroPredict AI integrates with Oracle APEX as an **enterprise data source** for agricultural and logistics organizations. This integration bridges legacy enterprise systems (running on Oracle Database with APEX/ORDS) with the AgroPredict AI prediction pipeline, enabling real-world data-driven predictions without requiring customers to migrate or duplicate their existing infrastructure.

## Architecture

### Role in the System

Oracle APEX serves two purposes:

1. **Read-only data ingestion** (primary) - Pulls agronomic field data (sensor readings, crop data, regional metrics) from Oracle APEX into PostgreSQL so the prediction pipeline operates on real enterprise data.
2. **Audited write-back** (break-glass) - Pushes prediction results and recommendations back into Oracle APEX tables, but only with explicit operator approval and a complete audit trail.

### Adapter Pattern

The integration uses a **two-layer adapter pattern**:

```
Oracle APEX / Oracle DB
    |
    |  (SQL via oracledb thin mode OR REST via ORDS/httpx)
    v
+----------------------------------+
|  OracleAPEXAdapter (Protocol)    |
|  - OracleSQLAdapter (oracledb)   |
|  - OracleRESTAdapter (httpx)     |
+----------------------------------+
    |
    v
+----------------------------------+
|       APEXService                |
|  - sync_data()                   |
|  - write_back()                  |
|  - Circuit breaker logic         |
+----------------------------------+
    |
    v
+----------------------------------+
|     APEXRepository (Protocol)    |
|  - InMemoryAPEXRepository (dev)  |
|  - PostgresAPEXRepository (prod) |
+----------------------------------+
    |
    v
+----------------------------------+
|     FieldDataResolver            |
|  - Bridges APEX data into        |
|    PredictionInput               |
+----------------------------------+
    |
    v
+----------------------------------+
|     PredictionService            |
|  - Uses resolved APEX data as    |
|    input for LangGraph graph     |
+----------------------------------+
```

## Components

### OracleAPEXAdapter Protocol

Defines the interface for all APEX data access:

```python
class OracleAPEXAdapter(Protocol):
    def fetch_data(self, query: str, params: dict | None) -> list[dict]: ...
    def write_data(self, table: str, data: dict, approved_by: str) -> dict: ...
    def health_check(self) -> bool: ...
```

### OracleSQLAdapter

Uses `oracledb` in thin mode for direct SQL execution against Oracle Database:

- **Connection pooling** with configurable min/max/increment
- **SELECT queries** return results as list of dicts with lowercase column names
- **INSERT operations** for write-back with automatic commit
- **Health check** via `SELECT 1 FROM DUAL`

### OracleRESTAdapter

Uses `httpx` to call ORDS (Oracle REST Data Services) endpoints:

- **GET requests** for data fetching (ORDS returns items in an "items" key)
- **POST requests** for write-back operations
- **Health check** via `/ords/_/health` endpoint
- **Basic authentication** with username/password

### APEXService

The service layer that orchestrates sync, write-back, and circuit breaker logic:

- **`sync_data()`** - Fetches data via adapter, validates records, persists field records to PostgreSQL
- **`write_back()`** - Requires explicit operator approval, writes to Oracle, creates audit record
- **`get_latest_field_record()`** - Looks up the most recent field record for tenant/crop/region
- **Circuit breaker** - Opens after 5 consecutive failures, blocks sync until recovery

### APEXRepository Protocol

Defines persistence operations for APEX state:

```python
class APEXRepository(Protocol):
    def save_connection(self, connection) -> OracleAPEXConnection: ...
    def get_connection(self, connection_id) -> OracleAPEXConnection | None: ...
    def save_sync_job(self, job) -> SyncJob: ...
    def get_sync_job(self, job_id) -> SyncJob | None: ...
    def save_writeback_audit(self, audit) -> WriteBackAudit: ...
    def get_writeback_audit(self, audit_id) -> WriteBackAudit | None: ...
    def list_writeback_audits(self, tenant_id) -> list[WriteBackAudit]: ...
    def save_field_record(self, record) -> APEXFieldRecord: ...
    def get_latest_field_record(self, tenant_id, crop, region) -> APEXFieldRecord | None: ...
```

### FieldDataResolver

Bridges APEX data into the prediction pipeline:

1. **Manual input** always wins if provided in the request
2. **APEX latest record** is looked up for tenant/crop/region
3. **Staleness check** triggers on-demand sync if data is older than the freshness window
4. **Degradation flags** are added when data is stale but still usable
5. **NoInputDataError** is raised when no source is available

### Credential Resolver

Resolves credential references (e.g., `vault://apex/creds`) to actual secrets:

- **`EnvironmentCredentialResolver`** - Maps references to environment variables for development
- **`VaultCredentialResolver`** - Integrates with HashiCorp Vault for production (stub)
- **`make_credential_resolver()`** - Factory that selects the appropriate resolver based on environment

## Data Flow

### Read Flow (Ingestion)

1. `POST /api/v1/apex/sync` triggers `APEXService.sync_data()`
2. The adapter (`OracleSQLAdapter` or `OracleRESTAdapter`) fetches data from Oracle APEX
3. Records are validated - invalid records are counted as quarantined
4. Valid records are persisted as `APEXFieldRecord` entries in PostgreSQL with:
   - Tenant ID, crop, region for scoping
   - Feature dict with all non-metadata fields
   - SHA-256 checksum for data integrity
   - Sync job ID for traceability
5. `FieldDataResolver` later fetches the latest record for a tenant/crop/region to populate prediction input
6. The prediction runs through the LangGraph graph with APEX-sourced features

### Write Flow (Write-Back)

1. A prediction is generated with recommendations
2. An operator explicitly approves write-back (`approved_by` field required)
3. `POST /api/v1/apex/writeback` triggers `APEXService.write_back()`
4. The adapter writes data to the specified Oracle APEX table
5. A `WriteBackAudit` record is created with:
   - Prediction ID
   - Approver identity and timestamp
   - Data written
   - Status (completed/failed)
6. If write-back fails, the audit record captures the error for retry and escalation

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/apex/connections` | Create a new APEX connection |
| GET | `/api/v1/apex/connections/{id}` | Get connection details |
| POST | `/api/v1/apex/sync` | Trigger data sync from APEX |
| POST | `/api/v1/apex/writeback` | Write prediction results back to APEX |
| GET | `/api/v1/apex/circuit/{id}` | Get circuit breaker state |
| GET | `/api/v1/apex/audits` | List write-back audit records |

## Database Tables

| Table | Purpose |
|-------|---------|
| `apex_connections` | APEX connection configurations with circuit breaker state |
| `apex_sync_jobs` | Sync job execution history and results |
| `apex_writeback_audits` | Complete audit trail for all write-back operations |
| `apex_field_records` | Resolved field data for prediction input (indexed by tenant/crop/region) |
| `apex_quarantined_records` | Invalid records held for analysis |

## Circuit Breaker

The circuit breaker protects the prediction pipeline from APEX failures:

- **CLOSED** (normal) - Sync operations proceed normally
- **OPEN** (after 5 failures) - Sync is blocked, job fails immediately
- **HALF_OPEN** (after recovery attempt) - Single test request to check if service is back

The circuit breaker state is persisted in the `apex_connections` table and survives restarts.

## Security

- **Credentials** are never stored in application config or environment variables committed to Git
- **Credential references** (e.g., `vault://apex/creds`) are resolved at runtime via Vault or External Secrets Operator
- **Write-back** requires explicit operator approval with full audit trail
- **Tenant isolation** is enforced at the repository level for all queries

## Local Development

Start Oracle XE for integration testing:

```bash
docker compose --profile oracle up -d
```

Set environment variables for the adapter:

```bash
export APEX_CREDS_USER=apex_user
export APEX_CREDS_PASSWORD=apex_pass
export APEX_CREDS_DSN=localhost:1521/APEXDB
```

## Design Principles

- **Non-invasive** - Read-only by default, never modifies operational data without approval
- **Resilient** - Circuit breaker protects the system if Oracle APEX becomes unavailable
- **Auditable** - Every write-back is recorded with who approved, when, what data, and the result
- **Adaptable** - Protocol pattern allows switching between SQL and REST without changing the rest of the system
- **Secure** - Credentials are referenced, not hardcoded; designed for Vault/ESO resolution
