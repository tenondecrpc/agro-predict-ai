from __future__ import annotations

import logging
import re
from typing import Any, Protocol, runtime_checkable

import httpx

from backend.integrations.oracle_apex.credentials import CredentialResolver, make_credential_resolver
from backend.integrations.oracle_apex.models import OracleAPEXConnection

logger = logging.getLogger(__name__)


@runtime_checkable
class OracleAPEXAdapter(Protocol):
    """Protocol for Oracle APEX data access.

    Implementations may use SQL (oracledb) or REST (httpx) to interact
    with Oracle APEX / ORDS endpoints.
    """

    def fetch_data(self, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...

    def write_data(
        self,
        table: str,
        data: dict[str, Any],
        approved_by: str,
    ) -> dict[str, Any]: ...

    def health_check(self) -> bool: ...


class OracleSQLAdapter:
    """Oracle APEX adapter using oracledb (thin mode) for SQL execution."""

    def __init__(
        self,
        *,
        dsn: str,
        user: str,
        password: str,
        pool_min: int = 2,
        pool_max: int = 10,
        pool_increment: int = 1,
        batch_size: int = 1000,
    ) -> None:
        import oracledb

        self._batch_size = batch_size
        self._pool = oracledb.create_pool(
            dsn=dsn,
            user=user,
            password=password,
            min=pool_min,
            max=pool_max,
            increment=pool_increment,
        )
        self._logger = logging.getLogger(__name__)

    @classmethod
    def from_credentials_ref(
        cls,
        credentials_ref: str,
        *,
        resolver: CredentialResolver | None = None,
        batch_size: int = 1000,
    ) -> OracleSQLAdapter:
        credentials = (resolver or make_credential_resolver()).resolve(credentials_ref)
        dsn = credentials.get("dsn")
        if not dsn:
            raise ValueError(f"Oracle SQL credentials for '{credentials_ref}' must include dsn.")
        return cls(
            dsn=dsn,
            user=credentials["user"],
            password=credentials["password"],
            batch_size=batch_size,
        )

    def fetch_data(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Execute a SELECT query and return results as list of dicts."""
        with self._pool.acquire() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params or {})
                columns = [col[0].lower() for col in cursor.description] if cursor.description else []
                rows: list[dict[str, Any]] = []
                while True:
                    batch = cursor.fetchmany(self._batch_size)
                    if not batch:
                        break
                    rows.extend(dict(zip(columns, row, strict=True)) for row in batch)
                return rows
            finally:
                cursor.close()

    def write_data(
        self,
        table: str,
        data: dict[str, Any],
        approved_by: str,
    ) -> dict[str, Any]:
        """Insert or update data in the specified Oracle table.

        By default this inserts all keys in ``data``. To update, pass
        ``{"_operation": "update", "_where": {"id": "..."}, ...}``.
        """
        table_name = _validate_sql_identifier(table)
        operation = str(data.get("_operation", "insert")).lower()
        values = {key: value for key, value in data.items() if key not in {"_operation", "_where"}}
        if not values:
            raise ValueError("write_data requires at least one data column.")

        if operation == "update":
            raw_where = data.get("_where")
            if not isinstance(raw_where, dict) or not raw_where:
                raise ValueError("UPDATE write_data requires a non-empty _where mapping.")
            columns = [_validate_sql_identifier(column) for column in values]
            where_columns = [_validate_sql_identifier(column) for column in raw_where]
            set_clause = ", ".join(f"{column} = :set_{column}" for column in columns)
            where_clause = " AND ".join(f"{column} = :where_{column}" for column in where_columns)
            sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
            bind_values = {
                **{f"set_{key}": value for key, value in values.items()},
                **{f"where_{key}": value for key, value in raw_where.items()},
            }
        elif operation == "insert":
            columns = [_validate_sql_identifier(column) for column in values]
            placeholders = [f":{column}" for column in columns]
            sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            bind_values = values
        else:
            raise ValueError("write_data _operation must be 'insert' or 'update'.")

        with self._pool.acquire() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, bind_values)
                conn.commit()
                return {
                    "rows_affected": cursor.rowcount,
                    "table": table,
                    "operation": operation,
                    "approved_by": approved_by,
                }
            finally:
                cursor.close()

    def health_check(self) -> bool:
        """Verify connectivity with SELECT 1 FROM DUAL."""
        try:
            with self._pool.acquire() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute("SELECT 1 FROM DUAL")
                    cursor.fetchone()
                    return True
                finally:
                    cursor.close()
        except Exception as exc:
            self._logger.error("oracle_health_check_failed", extra={"error": str(exc)})
            return False

    def close(self) -> None:
        """Close the connection pool."""
        self._pool.close()


class OracleRESTAdapter:
    """Oracle APEX adapter using ORDS REST API."""

    def __init__(
        self,
        *,
        base_url: str,
        username: str,
        password: str,
        timeout: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self._base_url,
            auth=(username, password),
            timeout=timeout,
        )
        self._logger = logging.getLogger(__name__)

    @classmethod
    def from_credentials_ref(
        cls,
        credentials_ref: str,
        *,
        base_url: str | None = None,
        resolver: CredentialResolver | None = None,
    ) -> OracleRESTAdapter:
        credentials = (resolver or make_credential_resolver()).resolve(credentials_ref)
        resolved_base_url = base_url or credentials.get("base_url")
        if not resolved_base_url:
            raise ValueError(f"Oracle REST credentials for '{credentials_ref}' must include base_url.")
        return cls(
            base_url=resolved_base_url,
            username=credentials["user"],
            password=credentials["password"],
        )

    def fetch_data(
        self,
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch data via ORDS REST endpoint.

        The query parameter is treated as a REST path (e.g., '/ords/schema/items/').
        For SQL queries, use OracleSQLAdapter instead.
        """
        response = self._client.get(query, params=params or {})
        response.raise_for_status()
        data = response.json()
        # ORDS returns items in an "items" key for collection endpoints
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        if isinstance(data, list):
            return data
        return [data]

    def write_data(
        self,
        table: str,
        data: dict[str, Any],
        approved_by: str,
    ) -> dict[str, Any]:
        """Write data via ORDS REST endpoint."""
        response = self._client.post(table, json=data)
        response.raise_for_status()
        return {"status": response.status_code, "table": table}

    def health_check(self) -> bool:
        """Verify connectivity via ORDS health endpoint."""
        try:
            response = self._client.get("/ords/_/health")
            return response.status_code == 200
        except Exception as exc:
            self._logger.error("oracle_rest_health_check_failed", extra={"error": str(exc)})
            return False

    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()


def build_adapter_from_connection(
    connection: OracleAPEXConnection,
    *,
    resolver: CredentialResolver | None = None,
    batch_size: int = 1000,
) -> OracleAPEXAdapter:
    credentials = (resolver or make_credential_resolver()).resolve(connection.credentials_ref)
    if connection.endpoint.startswith(("http://", "https://")) or "base_url" in credentials:
        return OracleRESTAdapter(
            base_url=credentials.get("base_url", connection.endpoint),
            username=credentials["user"],
            password=credentials["password"],
        )
    dsn = credentials.get("dsn")
    if not dsn:
        raise ValueError(f"Oracle SQL credentials for '{connection.credentials_ref}' must include dsn.")
    return OracleSQLAdapter(
        dsn=dsn,
        user=credentials["user"],
        password=credentials["password"],
        batch_size=batch_size,
    )


_SQL_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]*(?:\.[A-Za-z][A-Za-z0-9_$#]*)?$")


def _validate_sql_identifier(identifier: str) -> str:
    if not _SQL_IDENTIFIER.match(identifier):
        raise ValueError(f"Unsafe Oracle SQL identifier: {identifier}")
    return identifier
