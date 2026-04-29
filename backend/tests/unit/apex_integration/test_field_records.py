from __future__ import annotations

import pytest

from backend.integrations.oracle_apex.models import APEXFieldRecord, CircuitBreakerState, WriteBackRequest
from backend.integrations.oracle_apex.repository import InMemoryAPEXRepository
from backend.integrations.oracle_apex.service import APEXService
from backend.predictions.field_data_resolver import FieldDataResolver, NoInputDataError


class TestFieldRecordPersistence:
    """Test that sync_data persists field records."""

    def test_sync_persists_field_records(self) -> None:
        repo = InMemoryAPEXRepository()
        service = APEXService(repository=repo)

        conn = service.create_connection(
            "https://apex.example.com",
            "vault://apex/creds",
            tenant_id="tenant-1",
        )

        job = service.sync_data(
            conn.connection_id,
            "tenant-1",
            sample_data=[
                {"valid": True, "temperature": 22.5, "crop": "corn", "region": "north"},
                {"valid": True, "humidity": 65.0, "crop": "corn", "region": "north"},
                {"valid": False, "temperature": None},
            ],
            crop="corn",
            region="north",
        )

        assert job.status == "completed"
        assert job.records_ingested == 3
        assert job.records_quarantined == 1

        # Two valid records should be persisted as field records
        record = repo.get_latest_field_record("tenant-1", crop="corn", region="north")
        assert record is not None
        assert record.tenant_id == "tenant-1"
        assert record.crop == "corn"
        assert record.region == "north"
        assert record.checksum != ""
        assert record.sync_job_id == job.job_id

    def test_get_latest_field_record_returns_most_recent(self) -> None:
        repo = InMemoryAPEXRepository()
        service = APEXService(repository=repo)

        conn = service.create_connection(
            "https://apex.example.com",
            "vault://apex/creds",
            tenant_id="tenant-1",
        )

        # First sync
        service.sync_data(
            conn.connection_id,
            "tenant-1",
            sample_data=[
                {"valid": True, "temperature": 20.0, "crop": "corn", "region": "north"},
            ],
            crop="corn",
            region="north",
        )

        # Second sync with different value
        service.sync_data(
            conn.connection_id,
            "tenant-1",
            sample_data=[
                {"valid": True, "temperature": 25.0, "crop": "corn", "region": "north"},
            ],
            crop="corn",
            region="north",
        )

        record = repo.get_latest_field_record("tenant-1", crop="corn", region="north")
        assert record is not None
        # The latest record should have temperature 25.0
        assert record.features.get("temperature") == 25.0

    def test_get_latest_field_record_returns_none_for_missing(self) -> None:
        repo = InMemoryAPEXRepository()
        service = APEXService(repository=repo)

        record = service.get_latest_field_record(
            "tenant-1", crop="wheat", region="south",
        )
        assert record is None


class TestFieldDataResolver:
    """Test FieldDataResolver integration with APEXService."""

    def test_resolve_with_manual_input(self) -> None:
        resolver = FieldDataResolver(apex_service=None)

        result = resolver.resolve(
            tenant_id="tenant-1",
            crop="corn",
            region="north",
            manual_input={"temperature": 22.5, "humidity": 65.0},
        )

        assert result.source == "manual"
        assert result.feature_dict == {"temperature": 22.5, "humidity": 65.0}
        assert result.is_stale is False
        assert result.degradation_flags == []

    def test_resolve_fails_without_apex_or_manual(self) -> None:
        resolver = FieldDataResolver(apex_service=None)

        with pytest.raises(NoInputDataError, match="APEX service is not configured"):
            resolver.resolve(
                tenant_id="tenant-1",
                crop="corn",
                region="north",
                manual_input=None,
            )

    def test_resolve_from_apex_data(self) -> None:
        repo = InMemoryAPEXRepository()
        service = APEXService(repository=repo)

        conn = service.create_connection(
            "https://apex.example.com",
            "vault://apex/creds",
            tenant_id="tenant-1",
        )

        service.sync_data(
            conn.connection_id,
            "tenant-1",
            sample_data=[
                {"valid": True, "temperature": 22.5, "humidity": 65.0, "crop": "corn", "region": "north"},
            ],
            crop="corn",
            region="north",
        )

        resolver = FieldDataResolver(apex_service=service)

        result = resolver.resolve(
            tenant_id="tenant-1",
            crop="corn",
            region="north",
            manual_input=None,
        )

        assert result.source == "apex"
        assert "temperature" in result.feature_dict
        assert "humidity" in result.feature_dict
        assert result.feature_dict["temperature"] == 22.5
        assert result.feature_dict["humidity"] == 65.0
        assert result.provenance[0]["source_id"].startswith("apex:")

    def test_resolve_raises_when_no_apex_data(self) -> None:
        repo = InMemoryAPEXRepository()
        service = APEXService(repository=repo)

        resolver = FieldDataResolver(apex_service=service)

        with pytest.raises(NoInputDataError, match="No APEX data available"):
            resolver.resolve(
                tenant_id="tenant-1",
                crop="wheat",
                region="south",
                manual_input=None,
            )
