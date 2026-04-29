## ADDED Requirements

### Requirement: OracleAPEXAdapter protocol
The system SHALL define an `OracleAPEXAdapter` protocol with `fetch_data()`, `write_data()`, and `health_check()` methods for interacting with Oracle APEX.

#### Scenario: Protocol defines fetch_data method
- **WHEN** the `OracleAPEXAdapter` protocol is inspected
- **THEN** it declares `fetch_data(query: str, params: dict) -> list[dict]` for read-only data ingestion

#### Scenario: Protocol defines write_data method
- **WHEN** the `OracleAPEXAdapter` protocol is inspected
- **THEN** it declares `write_data(table: str, data: dict, approved_by: str) -> dict` for audited write-back

#### Scenario: Protocol defines health_check method
- **WHEN** the `OracleAPEXAdapter` protocol is inspected
- **THEN** it declares `health_check() -> bool` for connection validation

### Requirement: OracleAPEXAdapter implementation with oracledb
The system SHALL implement `OracleAPEXAdapter` using the `oracledb` Python driver in thin mode for SQL execution and `httpx` for REST calls.

#### Scenario: Adapter connects to Oracle via oracledb thin mode
- **WHEN** the adapter is initialized with a valid DSN and credentials
- **THEN** it creates an `oracledb` connection pool in thin mode without requiring Oracle Client libraries

#### Scenario: Adapter fetches data via SQL query
- **WHEN** `fetch_data()` is called with a SELECT query
- **THEN** it executes the query and returns results as a list of dictionaries

#### Scenario: Adapter fetches data via REST endpoint
- **WHEN** `fetch_data()` is called with a REST URL
- **THEN** it makes an HTTP GET request and returns the JSON response as a list of dictionaries

#### Scenario: Adapter writes data via SQL
- **WHEN** `write_data()` is called with a table name, data dict, and approver
- **THEN** it executes an INSERT or UPDATE statement and returns the affected row count

#### Scenario: Adapter health check validates connection
- **WHEN** `health_check()` is called
- **THEN** it executes `SELECT 1 FROM DUAL` and returns True if successful

#### Scenario: Adapter handles connection failure
- **WHEN** the Oracle database is unreachable
- **THEN** the adapter raises a connection error that the service layer can catch and record as a circuit breaker failure

### Requirement: Cursor-based pagination for large data syncs
The system SHALL support cursor-based pagination for large data synchronization to avoid memory exhaustion.

#### Scenario: Large query uses pagination
- **WHEN** `fetch_data()` is called with a query that returns more rows than the configured batch size
- **THEN** results are fetched in batches using a cursor and yielded incrementally

#### Scenario: Configurable batch size
- **WHEN** the adapter is configured with `batch_size=1000`
- **THEN** data is fetched in chunks of 1000 rows

### Requirement: Credential resolution from Vault or External Secrets
The system SHALL resolve Oracle APEX credentials at runtime via the `credentials_ref` field, not from plaintext storage.

#### Scenario: Credentials resolved from credentials_ref
- **WHEN** the adapter initializes a connection
- **THEN** it resolves the `credentials_ref` through the existing credentials module to obtain username, password, and DSN

#### Scenario: Credential rotation without restart
- **WHEN** credentials are rotated in Vault
- **THEN** the next sync job uses the new credentials without requiring a service restart
