from __future__ import annotations

import pytest

from backend.predictions.agents.explainability import ExplainabilityAgent
from backend.predictions.models import PredictionInput


class TestExplainabilityAgent:
    @pytest.fixture
    def agent(self) -> ExplainabilityAgent:
        return ExplainabilityAgent()

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

    def test_generates_explanation_artifact(self, agent: ExplainabilityAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 8.5,
            "confidence_interval": {"lower": 7.2, "upper": 9.8},
            "feature_importance": {"soil_moisture": 0.45, "temperature_c": 0.30, "rainfall_mm": 0.25},
            "model_version": "v1.2.0",
        }
        analyst_result = {
            "validated": True,
            "data_sources": [
                {"source_id": "weather-001", "validation_status": "passed"},
                {"source_id": "soil-002", "validation_status": "passed"},
            ],
            "uncertainty_flagged": False,
        }
        result = agent.execute(valid_input, ml_result, analyst_result)
        assert "feature_scores" in result
        assert "data_sources_used" in result
        assert "confidence_level" in result
        assert "uncertainty_factors" in result
        assert "human_readable_summary" in result

    def test_confidence_level_calculation(self, agent: ExplainabilityAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 8.5,
            "confidence_interval": {"lower": 7.2, "upper": 9.8},
            "feature_importance": {"soil_moisture": 0.45, "temperature_c": 0.30, "rainfall_mm": 0.25},
            "model_version": "v1.2.0",
        }
        analyst_result = {"validated": True, "data_sources": [], "uncertainty_flagged": False}
        result = agent.execute(valid_input, ml_result, analyst_result)
        assert 0.0 <= result["confidence_level"] <= 1.0
        # Narrow CI should yield higher confidence
        assert result["confidence_level"] > 0.5

    def test_low_confidence_highlights_uncertainty(
        self, agent: ExplainabilityAgent, valid_input: PredictionInput
    ) -> None:
        ml_result = {
            "prediction": 6.0,
            "confidence_interval": {"lower": 3.0, "upper": 9.0},  # Wide CI = low confidence
            "feature_importance": {"soil_moisture": 0.50, "temperature_c": 0.50},
            "model_version": "v1.2.0",
        }
        analyst_result = {"validated": True, "data_sources": [], "uncertainty_flagged": False}
        result = agent.execute(valid_input, ml_result, analyst_result)
        assert result["confidence_level"] < 0.7
        assert len(result["uncertainty_factors"]) > 0
        # Top uncertainty factors should be highlighted
        assert "wide_confidence_interval" in result["uncertainty_factors"]

    def test_data_sources_included(self, agent: ExplainabilityAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 8.5,
            "confidence_interval": {"lower": 7.2, "upper": 9.8},
            "feature_importance": {"soil_moisture": 0.45, "temperature_c": 0.30, "rainfall_mm": 0.25},
            "model_version": "v1.2.0",
        }
        analyst_result = {
            "validated": True,
            "data_sources": [
                {"source_id": "weather-001", "validation_status": "passed"},
                {"source_id": "soil-002", "validation_status": "passed"},
            ],
            "uncertainty_flagged": False,
        }
        result = agent.execute(valid_input, ml_result, analyst_result)
        assert "weather-001" in result["data_sources_used"]
        assert "soil-002" in result["data_sources_used"]

    def test_stale_data_uncertainty(self, agent: ExplainabilityAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 8.5,
            "confidence_interval": {"lower": 7.2, "upper": 9.8},
            "feature_importance": {"soil_moisture": 0.45},
            "model_version": "v1.2.0",
        }
        analyst_result = {
            "validated": True,
            "data_sources": [],
            "uncertainty_flagged": True,
            "uncertainty_reasons": ["stale_data"],
        }
        result = agent.execute(valid_input, ml_result, analyst_result)
        assert "stale_data" in result["uncertainty_factors"]
        assert result["confidence_level"] < 0.85  # Reduced due to stale data
