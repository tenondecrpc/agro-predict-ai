from __future__ import annotations

import pytest

from backend.data_ingestion.models import (
    DataSource,
    DataSourceType,
    IngestionBatch,
    QualityStatus,
)
from backend.data_ingestion.repository import InMemoryDataRepository
from backend.data_ingestion.service import IngestionService


class TestIngestionService:
    @pytest.fixture
    def service(self) -> IngestionService:
        return IngestionService(repository=InMemoryDataRepository())

    def test_ingest_single_valid(self, service: IngestionService) -> None:
        from datetime import UTC, datetime
        rec = service.ingest_single(
            "src-1",
            "t1",
            "team-a",
            {"temperature": 22.5, "humidity": 60, "timestamp": datetime.now(UTC).isoformat()},
            required_fields=["temperature", "humidity"],
            range_rules={"temperature": (0.0, 50.0)},
        )
        assert rec.quality_status == QualityStatus.PASSED
        assert rec.provenance_id is not None

    def test_ingest_single_quarantined(self, service: IngestionService) -> None:
        rec = service.ingest_single(
            "src-1",
            "t1",
            "team-a",
            {"temperature": 22.5},
            required_fields=["temperature", "humidity"],
        )
        assert rec.quality_status == QualityStatus.QUARANTINED

    def test_ingest_batch(self, service: IngestionService) -> None:
        from datetime import UTC, datetime
        batch = IngestionBatch(
            source_id="src-1",
            tenant_id="t1",
            team_id="team-a",
            records=[
                {"temperature": 22.5, "humidity": 60, "timestamp": datetime.now(UTC).isoformat()},
                {"temperature": 23.0, "humidity": 55, "timestamp": datetime.now(UTC).isoformat()},
            ],
        )
        summary = service.ingest_batch(batch, required_fields=["temperature", "humidity"])
        assert summary.ingested == 2
        assert summary.errors == 0

    def test_get_quality_summary(self, service: IngestionService) -> None:
        service.ingest_single("src-1", "t1", "team-a", {"temperature": 22.5}, required_fields=["humidity"])
        summary = service.get_quality_summary("t1")
        assert summary.total_records == 1
        assert summary.quarantined_count == 1

    def test_register_and_get_source(self, service: IngestionService) -> None:
        src = DataSource(name="Weather A", source_type=DataSourceType.WEATHER_API, tenant_id="t1")
        saved = service.register_source(src)
        assert saved.source_id is not None
        fetched = service.get_source(saved.source_id)
        assert fetched is not None
        assert fetched.name == "Weather A"
