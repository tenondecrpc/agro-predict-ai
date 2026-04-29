from __future__ import annotations

from datetime import UTC

import pytest

from backend.data_ingestion.models import DataRecord, GateType, QualityStatus
from backend.data_ingestion.quality import QualityGateEngine


class TestQualityGateEngine:
    @pytest.fixture
    def engine(self) -> QualityGateEngine:
        return QualityGateEngine()

    def test_completeness_pass(self, engine: QualityGateEngine) -> None:
        rec = DataRecord(
            source_id="src-1",
            tenant_id="t1",
            team_id="team-a",
            data_payload={"temperature": 22.5, "humidity": 60, "soil_moisture": 0.35},
        )
        result = engine.evaluate_completeness(rec, required_fields=["temperature", "humidity"])
        assert result.passed is True
        assert result.gate_type == GateType.COMPLETENESS

    def test_completeness_fail(self, engine: QualityGateEngine) -> None:
        rec = DataRecord(
            source_id="src-1",
            tenant_id="t1",
            team_id="team-a",
            data_payload={"temperature": 22.5},
        )
        result = engine.evaluate_completeness(rec, required_fields=["temperature", "humidity"])
        assert result.passed is False
        assert "humidity" in result.message

    def test_freshness_pass(self, engine: QualityGateEngine) -> None:
        from datetime import datetime
        rec = DataRecord(
            source_id="src-1",
            tenant_id="t1",
            team_id="team-a",
            data_payload={"timestamp": datetime.now(UTC).isoformat()},
        )
        result = engine.evaluate_freshness(rec, max_age_hours=48)
        assert result.passed is True

    def test_freshness_fail(self, engine: QualityGateEngine) -> None:
        from datetime import datetime, timedelta
        rec = DataRecord(
            source_id="src-1",
            tenant_id="t1",
            team_id="team-a",
            data_payload={"timestamp": (datetime.now(UTC) - timedelta(hours=72)).isoformat()},
        )
        result = engine.evaluate_freshness(rec, max_age_hours=48)
        assert result.passed is False

    def test_range_pass(self, engine: QualityGateEngine) -> None:
        rec = DataRecord(
            source_id="src-1",
            tenant_id="t1",
            team_id="team-a",
            data_payload={"temperature": 22.5},
        )
        result = engine.evaluate_range(rec, field="temperature", min_val=0.0, max_val=50.0)
        assert result.passed is True

    def test_range_fail(self, engine: QualityGateEngine) -> None:
        rec = DataRecord(
            source_id="src-1",
            tenant_id="t1",
            team_id="team-a",
            data_payload={"temperature": 60.0},
        )
        result = engine.evaluate_range(rec, field="temperature", min_val=0.0, max_val=50.0)
        assert result.passed is False

    def test_full_pipeline_pass(self, engine: QualityGateEngine) -> None:
        from datetime import datetime
        rec = DataRecord(
            source_id="src-1",
            tenant_id="t1",
            team_id="team-a",
            data_payload={"temperature": 22.5, "humidity": 60, "timestamp": datetime.now(UTC).isoformat()},
        )
        results = engine.evaluate_all(
            rec,
            required_fields=["temperature", "humidity"],
            range_rules={"temperature": (0.0, 50.0)},
        )
        assert all(r.passed for r in results)
        assert rec.quality_status == QualityStatus.PASSED

    def test_full_pipeline_fail(self, engine: QualityGateEngine) -> None:
        rec = DataRecord(
            source_id="src-1",
            tenant_id="t1",
            team_id="team-a",
            data_payload={"temperature": 60.0},
        )
        results = engine.evaluate_all(
            rec,
            required_fields=["temperature", "humidity"],
            range_rules={"temperature": (0.0, 50.0)},
        )
        assert any(not r.passed for r in results)
        assert rec.quality_status == QualityStatus.QUARANTINED
