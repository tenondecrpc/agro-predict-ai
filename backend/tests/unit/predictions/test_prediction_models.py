from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.predictions.models import (
    AgentExecutionRecord,
    DataProvenanceEntry,
    ExplanationArtifactModel,
    PredictionInput,
    PredictionOutput,
    PredictionState,
    PredictionStatus,
)


class TestPredictionInput:
    def test_valid_input(self) -> None:
        inp = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={
                "soil_moisture": 0.35,
                "temperature_c": 22.5,
                "rainfall_mm": 45.0,
            },
        )
        assert inp.crop == "corn"
        assert inp.region == "midwest_us"
        assert inp.time_horizon_days == 30
        assert inp.input_data_hash is not None
        assert len(inp.input_data_hash) == 64  # SHA-256 hex

    def test_missing_required_field(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            PredictionInput(
                tenant_id="tenant-alpha",
                team_id="team-core",
                crop="corn",
                region="midwest_us",
                time_horizon_days=30,
            )
        assert "input_data" in str(exc_info.value)

    def test_invalid_time_horizon(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            PredictionInput(
                tenant_id="tenant-alpha",
                team_id="team-core",
                crop="corn",
                region="midwest_us",
                time_horizon_days=0,
                input_data={"soil_moisture": 0.35},
            )
        assert "time_horizon_days" in str(exc_info.value)

    def test_input_data_hash_is_deterministic(self) -> None:
        inp1 = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35},
        )
        inp2 = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35},
        )
        assert inp1.input_data_hash == inp2.input_data_hash

    def test_json_serialization(self) -> None:
        inp = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35},
        )
        raw = inp.model_dump_json()
        loaded = PredictionInput.model_validate_json(raw)
        assert loaded.crop == "corn"


class TestPredictionOutput:
    def test_valid_output(self) -> None:
        out = PredictionOutput(
            prediction_id="pred-123",
            tenant_id="tenant-alpha",
            model_version="v1.2.0",
            status=PredictionStatus.COMPLETED,
            output={"yield_tons_per_hectare": 8.5},
            confidence_interval={"lower": 7.2, "upper": 9.8},
            feature_importance={"soil_moisture": 0.45, "temperature_c": 0.30},
            data_provenance=[
                DataProvenanceEntry(
                    source_id="weather-station-001",
                    ingested_at=datetime.now(UTC),
                    validation_status="passed",
                    checksum="abc123",
                )
            ],
            explanation_artifact=ExplanationArtifactModel(
                feature_scores={"soil_moisture": 0.45},
                data_sources_used=["weather-station-001"],
                confidence_level=0.85,
                uncertainty_factors=["rainfall_variance"],
                human_readable_summary="Soil moisture is the primary driver.",
            ),
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        assert out.status == PredictionStatus.COMPLETED
        assert out.confidence_interval["lower"] < out.confidence_interval["upper"]

    def test_invalid_confidence_interval(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            PredictionOutput(
                prediction_id="pred-123",
                tenant_id="tenant-alpha",
                model_version="v1.2.0",
                status=PredictionStatus.COMPLETED,
                output={"yield_tons_per_hectare": 8.5},
                confidence_interval={"lower": 9.8, "upper": 7.2},
                feature_importance={},
                data_provenance=[],
                created_at=datetime.now(UTC),
            )
        assert "lower" in str(exc_info.value) or "upper" in str(exc_info.value)

    def test_json_serialization(self) -> None:
        out = PredictionOutput(
            prediction_id="pred-123",
            tenant_id="tenant-alpha",
            model_version="v1.2.0",
            status=PredictionStatus.COMPLETED,
            output={"yield_tons_per_hectare": 8.5},
            confidence_interval={"lower": 7.2, "upper": 9.8},
            feature_importance={"soil_moisture": 0.45},
            data_provenance=[],
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        raw = out.model_dump_json()
        loaded = PredictionOutput.model_validate_json(raw)
        assert loaded.prediction_id == "pred-123"


class TestAgentExecutionRecord:
    def test_record_creation(self) -> None:
        rec = AgentExecutionRecord(
            prediction_id="pred-123",
            agent_name="data_analyst",
            input_state={"input_data": {"soil_moisture": 0.35}},
            output_state={"validated": True},
            duration_ms=150,
            status="success",
        )
        assert rec.agent_name == "data_analyst"
        assert rec.status == "success"

    def test_invalid_status(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            AgentExecutionRecord(
                prediction_id="pred-123",
                agent_name="data_analyst",
                input_state={},
                output_state={},
                duration_ms=100,
                status="invalid_status",
            )
        assert "status" in str(exc_info.value)


class TestPredictionState:
    def test_state_creation(self) -> None:
        state = PredictionState(
            input=PredictionInput(
                tenant_id="tenant-alpha",
                team_id="team-core",
                crop="corn",
                region="midwest_us",
                time_horizon_days=30,
                input_data={"soil_moisture": 0.35},
            ),
        )
        assert state["input"].crop == "corn"
        assert state.get("output") is None
        assert state.get("error") is None

    def test_state_with_output(self) -> None:
        state = PredictionState(
            input=PredictionInput(
                tenant_id="tenant-alpha",
                team_id="team-core",
                crop="corn",
                region="midwest_us",
                time_horizon_days=30,
                input_data={"soil_moisture": 0.35},
            ),
            output=PredictionOutput(
                prediction_id="pred-123",
                tenant_id="tenant-alpha",
                model_version="v1.2.0",
                status=PredictionStatus.COMPLETED,
                output={"yield_tons_per_hectare": 8.5},
                confidence_interval={"lower": 7.2, "upper": 9.8},
                feature_importance={"soil_moisture": 0.45},
                data_provenance=[],
                created_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
            ),
        )
        assert state["output"].prediction_id == "pred-123"


class TestExplanationArtifactModel:
    def test_artifact_creation(self) -> None:
        art = ExplanationArtifactModel(
            feature_scores={"soil_moisture": 0.45, "temperature_c": 0.30},
            data_sources_used=["weather-station-001", "satellite-imagery-002"],
            confidence_level=0.85,
            uncertainty_factors=["rainfall_variance"],
            human_readable_summary="Soil moisture is the primary driver of yield prediction.",
        )
        assert art.confidence_level == 0.85
        assert len(art.data_sources_used) == 2

    def test_confidence_level_bounds(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ExplanationArtifactModel(
                feature_scores={},
                data_sources_used=[],
                confidence_level=1.5,
                uncertainty_factors=[],
                human_readable_summary="test",
            )
        assert "confidence_level" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ExplanationArtifactModel(
                feature_scores={},
                data_sources_used=[],
                confidence_level=-0.1,
                uncertainty_factors=[],
                human_readable_summary="test",
            )
        assert "confidence_level" in str(exc_info.value)
