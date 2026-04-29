from __future__ import annotations

import logging
from typing import Any, Protocol, runtime_checkable

import httpx

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
    ) -> None:
        import oracledb
        self._pool = oracledb.create_pool(
            dsn=dsn,
            user=user,
            password=password,
            min=pool_min,
            max=pool_max,
            increment=pool_increment,
        )
        self._logger = logging.getLogger(__name__)

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
                return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
            finally:
                cursor.close()

    def write_data(
        self,
        table: str,
        data: dict[str, Any],
        approved_by: str,
    ) -> dict[str, Any]:
        """Insert data into the specified table."""
        columns = list(data.keys())
        placeholders = [f":{col}" for col in columns]
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"

        with self._pool.acquire() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, data)
                conn.commit()
                return {"rows_affected": cursor.rowcount, "table": table}
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
