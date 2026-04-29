from __future__ import annotations

import pytest

from backend.predictions.agents.recommendation_engine import RecommendationEngineAgent
from backend.predictions.models import PredictionInput


class TestRecommendationEngineAgent:
    @pytest.fixture
    def agent(self) -> RecommendationEngineAgent:
        return RecommendationEngineAgent()

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

    def test_generates_recommendation(self, agent: RecommendationEngineAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 8.5,
            "confidence_interval": {"lower": 7.2, "upper": 9.8},
            "feature_importance": {"soil_moisture": 0.45, "temperature_c": 0.30, "rainfall_mm": 0.25},
            "model_version": "v1.2.0",
        }
        result = agent.execute(valid_input, ml_result)
        assert "recommendation" in result
        assert "priority" in result
        assert "actions" in result
        assert isinstance(result["actions"], list)
        assert len(result["actions"]) > 0

    def test_high_yield_recommendation(self, agent: RecommendationEngineAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 12.0,
            "confidence_interval": {"lower": 11.0, "upper": 13.0},
            "feature_importance": {"soil_moisture": 0.45, "temperature_c": 0.30, "rainfall_mm": 0.25},
            "model_version": "v1.2.0",
        }
        result = agent.execute(valid_input, ml_result)
        assert result["priority"] == "low"
        assert "maintain" in result["recommendation"].lower()

    def test_low_yield_recommendation(self, agent: RecommendationEngineAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 4.0,
            "confidence_interval": {"lower": 3.0, "upper": 5.0},
            "feature_importance": {"soil_moisture": 0.60, "temperature_c": 0.20, "rainfall_mm": 0.20},
            "model_version": "v1.2.0",
        }
        result = agent.execute(valid_input, ml_result)
        assert result["priority"] == "high"
        assert any("irrigation" in action.lower() for action in result["actions"])

    def test_recommendation_includes_context(
        self, agent: RecommendationEngineAgent, valid_input: PredictionInput
    ) -> None:
        ml_result = {
            "prediction": 8.5,
            "confidence_interval": {"lower": 7.2, "upper": 9.8},
            "feature_importance": {"soil_moisture": 0.45, "temperature_c": 0.30, "rainfall_mm": 0.25},
            "model_version": "v1.2.0",
        }
        result = agent.execute(valid_input, ml_result)
        assert valid_input.crop in result["recommendation"]
        assert valid_input.region in result["recommendation"]

    def test_degraded_recommendation(self, agent: RecommendationEngineAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 6.0,
            "confidence_interval": {"lower": 4.0, "upper": 8.0},
            "feature_importance": {"soil_moisture": 0.50},
            "model_version": "cached",
            "staleness_warning": True,
            "degradation_flags": ["cached_model_fallback"],
        }
        result = agent.execute(valid_input, ml_result)
        assert result["degraded"] is True
        assert "caution" in result["recommendation"].lower() or "uncertainty" in result["recommendation"].lower()
