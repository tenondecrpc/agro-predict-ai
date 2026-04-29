from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.integrations.oracle_apex.models import CircuitBreakerState, WriteBackRequest
from backend.integrations.oracle_apex.repository import InMemoryAPEXRepository
from backend.integrations.oracle_apex.service import APEXService


class TestAPEXService:
    @pytest.fixture
    def service(self) -> APEXService:
        return APEXService(repository=InMemoryAPEXRepository())

    def test_create_connection(self, service: APEXService) -> None:
        conn = service.create_connection("https://apex.example.com", "vault://apex/creds")
        assert conn.endpoint == "https://apex.example.com"
        assert conn.circuit_breaker_state == CircuitBreakerState.CLOSED

    def test_sync_success(self, service: APEXService) -> None:
        conn = service.create_connection(
            "https://apex.example.com",
            "vault://apex/creds",
            tenant_id="tenant-1",
        )
        job = service.sync_data(
            conn.connection_id,
            "tenant-1",
            sample_data=[
                {"valid": True, "temperature": 22.5},
                {"valid": True, "temperature": 23.0},
            ],
        )
        assert job.status == "completed"
        assert job.records_ingested == 2
        assert job.records_quarantined == 0

    def test_sync_with_quarantine(self, service: APEXService) -> None:
        conn = service.create_connection(
            "https://apex.example.com",
            "vault://apex/creds",
            tenant_id="tenant-1",
        )
        job = service.sync_data(
            conn.connection_id,
            "tenant-1",
            sample_data=[
                {"valid": True, "temperature": 22.5},
                {"valid": False, "temperature": None},
            ],
        )
        assert job.records_ingested == 2
        assert job.records_quarantined == 1

    def test_sync_circuit_breaker_open(self, service: APEXService) -> None:
        conn = service.create_connection(
            "https://apex.example.com",
            "vault://apex/creds",
            tenant_id="tenant-1",
        )
        # Force circuit open
        for _ in range(5):
            conn.record_failure()
        service.repository.save_connection(conn)

        job = service.sync_data(conn.connection_id, "tenant-1")
        assert job.status == "failed"
        assert "Circuit breaker" in job.error_message

    def test_write_back_requires_approval(self, service: APEXService) -> None:
        req = WriteBackRequest(
            prediction_id="pred-123",
            oracle_apex_table="PREDICTIONS",
            data_written={"yield": 8.5},
            approved_by="",
        )
        with pytest.raises(ValueError, match="approval"):
            service.write_back(req, tenant_id="t1")

    def test_write_back_success(self, service: APEXService) -> None:
        req = WriteBackRequest(
            prediction_id="pred-123",
            oracle_apex_table="PREDICTIONS",
            data_written={"yield": 8.5},
            approved_by="admin@example.com",
        )
        audit = service.write_back(req, tenant_id="t1")
        assert audit.status == "completed"
        assert audit.approved_by == "admin@example.com"
        assert audit.tenant_id == "t1"

    def test_sync_uses_adapter_records(self) -> None:
        repo = InMemoryAPEXRepository()
        adapter = MagicMock()
        adapter.fetch_data.return_value = [{"valid": True, "temperature": 21.0}]
        service = APEXService(repository=repo, adapter=adapter)
        conn = service.create_connection(
            "SELECT * FROM FIELD_DATA",
            "vault://apex/creds",
            tenant_id="tenant-1",
        )

        job = service.sync_data(conn.connection_id, "tenant-1")

        assert job.status == "completed"
        assert job.records_ingested == 1
        adapter.fetch_data.assert_called_once_with("SELECT * FROM FIELD_DATA")

    def test_write_back_uses_adapter(self) -> None:
        repo = InMemoryAPEXRepository()
        adapter = MagicMock()
        service = APEXService(repository=repo, adapter=adapter)
        req = WriteBackRequest(
            prediction_id="pred-123",
            oracle_apex_table="PREDICTIONS",
            data_written={"yield": 8.5},
            approved_by="admin@example.com",
        )

        audit = service.write_back(req, tenant_id="tenant-1")

        assert audit.status == "completed"
        adapter.write_data.assert_called_once_with(
            "PREDICTIONS",
            {"yield": 8.5},
            "admin@example.com",
        )

    def test_circuit_state_closed(self, service: APEXService) -> None:
        conn = service.create_connection("https://apex.example.com", "vault://apex/creds")
        state = service.get_circuit_state(conn.connection_id)
        assert state["state"] == "closed"

    def test_circuit_state_open(self, service: APEXService) -> None:
        conn = service.create_connection("https://apex.example.com", "vault://apex/creds")
        for _ in range(5):
            conn.record_failure()
        service.repository.save_connection(conn)
        state = service.get_circuit_state(conn.connection_id)
        assert state["state"] == "open"
        assert state["failure_count"] == 5
