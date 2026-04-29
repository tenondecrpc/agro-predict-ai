from __future__ import annotations

import pytest

from backend.predictions.graph import PredictionGraph
from backend.predictions.models import PredictionInput, PredictionStatus


class TestPredictionGraph:
    @pytest.fixture
    def graph(self) -> PredictionGraph:
        return PredictionGraph()

    @pytest.fixture
    def valid_input(self) -> PredictionInput:
        return PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35, "temperature_c": 22.5, "rainfall_mm": 45.0},
        )

    def test_successful_end_to_end(self, graph: PredictionGraph, valid_input: PredictionInput) -> None:
        result = graph.execute(valid_input, model_version="v1.2.0")
        assert result is not None
        assert result.status in (PredictionStatus.COMPLETED, PredictionStatus.DEGRADED)
        assert result.output is not None
        assert result.confidence_interval is not None
        assert result.explanation_artifact is not None
        assert result.data_provenance is not None

    def test_graph_records_agent_executions(self, graph: PredictionGraph, valid_input: PredictionInput) -> None:
        result, executions = graph.execute_with_metadata(valid_input, model_version="v1.2.0")
        assert executions is not None
        agent_names = {e.agent_name for e in executions}
        assert "data_analyst" in agent_names
        assert "ml_executor" in agent_names
        assert "recommendation_engine" in agent_names
        assert "explainability" in agent_names
        assert "reviewer" in agent_names

    def test_stale_data_flags_uncertainty(self, graph: PredictionGraph) -> None:
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
                "data_freshness_hours": 72,
            },
        )
        result = graph.execute(inp, model_version="v1.2.0")
        assert result.status == PredictionStatus.COMPLETED
        assert result.explanation_artifact is not None
        assert "stale_data" in result.explanation_artifact.uncertainty_factors

    def test_missing_required_field_escalates(self, graph: PredictionGraph) -> None:
        inp = PredictionInput(
            tenant_id="tenant-alpha",
            team_id="team-core",
            crop="corn",
            region="midwest_us",
            time_horizon_days=30,
            input_data={"soil_moisture": 0.35},  # missing temperature_c and rainfall_mm
        )
        result = graph.execute(inp, model_version="v1.2.0")
        assert result.status == PredictionStatus.ESCALATED
        assert result.escalation_reason is not None

    def test_contradictory_data_escalates(self, graph: PredictionGraph) -> None:
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
                "soil_moisture_secondary": 0.10,
            },
        )
        result = graph.execute(inp, model_version="v1.2.0")
        assert result.status == PredictionStatus.ESCALATED
        assert "contradiction" in (result.escalation_reason or "").lower()
