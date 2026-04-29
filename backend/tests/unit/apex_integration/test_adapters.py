from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from backend.integrations.oracle_apex.adapter import OracleRESTAdapter


@pytest.fixture
def mock_oracledb() -> MagicMock:
    """Provide a mocked oracledb module for SQL adapter tests."""
    mock = MagicMock()
    mock_pool = MagicMock()
    mock.create_pool.return_value = mock_pool
    with patch.dict(sys.modules, {"oracledb": mock}):
        yield mock, mock_pool


class TestOracleSQLAdapter:
    """Tests for OracleSQLAdapter using mocked oracledb."""

    def test_init_creates_pool(self, mock_oracledb: tuple) -> None:
        mock, mock_pool = mock_oracledb

        # Import after mocking
        from backend.integrations.oracle_apex.adapter import OracleSQLAdapter

        adapter = OracleSQLAdapter(
            dsn="localhost:1521/XE",
            user="test_user",
            password="test_pass",
        )

        mock.create_pool.assert_called_once_with(
            dsn="localhost:1521/XE",
            user="test_user",
            password="test_pass",
            min=2,
            max=10,
            increment=1,
        )
        adapter.close()

    def test_fetch_data_returns_dicts(self, mock_oracledb: tuple) -> None:
        mock, mock_pool = mock_oracledb

        from backend.integrations.oracle_apex.adapter import OracleSQLAdapter

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("name",), ("value",)]
        mock_cursor.fetchmany.side_effect = [
            [
            (1, "temperature", 22.5),
            (2, "humidity", 65.0),
            ],
            [],
        ]
        mock_pool.acquire.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        adapter = OracleSQLAdapter(
            dsn="localhost:1521/XE",
            user="test_user",
            password="test_pass",
        )

        result = adapter.fetch_data("SELECT * FROM field_data")

        assert len(result) == 2
        assert result[0] == {"id": 1, "name": "temperature", "value": 22.5}
        assert result[1] == {"id": 2, "name": "humidity", "value": 65.0}
        adapter.close()

    def test_fetch_data_with_params(self, mock_oracledb: tuple) -> None:
        mock, mock_pool = mock_oracledb

        from backend.integrations.oracle_apex.adapter import OracleSQLAdapter

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.description = [("id",), ("crop",)]
        mock_cursor.fetchmany.side_effect = [[(1, "corn")], []]
        mock_pool.acquire.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        adapter = OracleSQLAdapter(
            dsn="localhost:1521/XE",
            user="test_user",
            password="test_pass",
        )

        adapter.fetch_data("SELECT * FROM crops WHERE region = :region", {"region": "north"})

        mock_cursor.execute.assert_called_once_with(
            "SELECT * FROM crops WHERE region = :region",
            {"region": "north"},
        )
        adapter.close()

    def test_write_data_inserts(self, mock_oracledb: tuple) -> None:
        mock, mock_pool = mock_oracledb

        from backend.integrations.oracle_apex.adapter import OracleSQLAdapter

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_pool.acquire.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        adapter = OracleSQLAdapter(
            dsn="localhost:1521/XE",
            user="test_user",
            password="test_pass",
        )

        result = adapter.write_data(
            "PREDICTIONS",
            {"prediction_id": "p1", "yield": 8.5},
            approved_by="admin@example.com",
        )

        assert result["rows_affected"] == 1
        assert result["table"] == "PREDICTIONS"
        mock_cursor.execute.assert_called_once()
        sql = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO PREDICTIONS" in sql
        mock_conn.commit.assert_called_once()
        adapter.close()

    def test_health_check_success(self, mock_oracledb: tuple) -> None:
        mock, mock_pool = mock_oracledb

        from backend.integrations.oracle_apex.adapter import OracleSQLAdapter

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_pool.acquire.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        adapter = OracleSQLAdapter(
            dsn="localhost:1521/XE",
            user="test_user",
            password="test_pass",
        )

        assert adapter.health_check() is True
        mock_cursor.execute.assert_called_once_with("SELECT 1 FROM DUAL")
        adapter.close()

    def test_health_check_failure(self, mock_oracledb: tuple) -> None:
        mock, mock_pool = mock_oracledb
        mock_pool.acquire.side_effect = Exception("Connection refused")

        from backend.integrations.oracle_apex.adapter import OracleSQLAdapter

        adapter = OracleSQLAdapter(
            dsn="localhost:1521/XE",
            user="test_user",
            password="test_pass",
        )

        assert adapter.health_check() is False
        adapter.close()


class TestOracleRESTAdapter:
    """Tests for OracleRESTAdapter using mocked httpx."""

    def test_init_sets_base_url(self) -> None:
        with patch("httpx.Client"):
            adapter = OracleRESTAdapter(
                base_url="https://apex.example.com/ords/",
                username="test_user",
                password="test_pass",
            )
            assert adapter._base_url == "https://apex.example.com/ords"

    def test_fetch_data_returns_items_from_dict(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {"id": 1, "temperature": 22.5},
                {"id": 2, "temperature": 23.0},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            adapter = OracleRESTAdapter(
                base_url="https://apex.example.com",
                username="test_user",
                password="test_pass",
            )

            result = adapter.fetch_data("/ords/schema/field_data/")

            assert len(result) == 2
            assert result[0]["temperature"] == 22.5
            mock_client.get.assert_called_once_with(
                "/ords/schema/field_data/",
                params={},
            )

    def test_fetch_data_returns_list_directly(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"id": 1, "temperature": 22.5},
        ]
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            adapter = OracleRESTAdapter(
                base_url="https://apex.example.com",
                username="test_user",
                password="test_pass",
            )

            result = adapter.fetch_data("/ords/schema/items/")

            assert len(result) == 1
            assert result[0]["id"] == 1

    def test_fetch_data_with_params(self) -> None:
        mock_response = MagicMock()
        mock_response.json.return_value = {"items": []}
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            adapter = OracleRESTAdapter(
                base_url="https://apex.example.com",
                username="test_user",
                password="test_pass",
            )

            adapter.fetch_data("/ords/schema/items/", params={"region": "north"})

            mock_client.get.assert_called_once_with(
                "/ords/schema/items/",
                params={"region": "north"},
            )

    def test_write_data_posts(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            adapter = OracleRESTAdapter(
                base_url="https://apex.example.com",
                username="test_user",
                password="test_pass",
            )

            result = adapter.write_data(
                "/ords/schema/predictions/",
                {"prediction_id": "p1", "yield": 8.5},
                approved_by="admin@example.com",
            )

            assert result["status"] == 201
            assert result["table"] == "/ords/schema/predictions/"
            mock_client.post.assert_called_once_with(
                "/ords/schema/predictions/",
                json={"prediction_id": "p1", "yield": 8.5},
            )

    def test_health_check_success(self) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with patch("httpx.Client", return_value=mock_client):
            adapter = OracleRESTAdapter(
                base_url="https://apex.example.com",
                username="test_user",
                password="test_pass",
            )

            assert adapter.health_check() is True
            mock_client.get.assert_called_once_with("/ords/_/health")

    def test_health_check_failure(self) -> None:
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection refused")

        with patch("httpx.Client", return_value=mock_client):
            adapter = OracleRESTAdapter(
                base_url="https://apex.example.com",
                username="test_user",
                password="test_pass",
            )

            assert adapter.health_check() is False

    def test_close_closes_client(self) -> None:
        mock_client = MagicMock()

        with patch("httpx.Client", return_value=mock_client):
            adapter = OracleRESTAdapter(
                base_url="https://apex.example.com",
                username="test_user",
                password="test_pass",
            )
            adapter.close()

            mock_client.close.assert_called_once()
