from __future__ import annotations

import pytest

from backend.predictions.agents.ml_executor import MLExecutorAgent, ModelUnavailableError
from backend.predictions.models import PredictionInput


class TestMLExecutorAgent:
    @pytest.fixture
    def agent(self) -> MLExecutorAgent:
        return MLExecutorAgent()

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

    def test_successful_execution(self, agent: MLExecutorAgent, valid_input: PredictionInput) -> None:
        result = agent.execute(valid_input, model_version="v1.2.0")
        assert "prediction" in result
        assert "confidence_interval" in result
        assert "feature_importance" in result
        assert "model_version" in result
        assert result["model_version"] == "v1.2.0"
        assert result["status"] == "success"
        ci = result["confidence_interval"]
        assert ci["lower"] < ci["upper"]

    def test_invalid_model_version(self, agent: MLExecutorAgent, valid_input: PredictionInput) -> None:
        with pytest.raises(ModelUnavailableError):
            agent.execute(valid_input, model_version="nonexistent")

    def test_cached_model_fallback(self, agent: MLExecutorAgent, valid_input: PredictionInput) -> None:
        # First simulate primary model failure by forcing it
        with pytest.raises(ModelUnavailableError):
            agent.execute(valid_input, model_version="nonexistent")

        # Now test explicit fallback path
        result = agent.execute_with_fallback(valid_input, primary_version="v1.2.0")
        assert result["status"] == "success"

    def test_fallback_returns_staleness_warning(self, agent: MLExecutorAgent, valid_input: PredictionInput) -> None:
        # Simulate scenario where primary fails and we use cached
        result = agent.execute_with_fallback(
            valid_input,
            primary_version="v1.2.0",
            force_fallback=True,
        )
        assert result["status"] == "degraded"
        assert result["staleness_warning"] is True
        assert "cached_model_fallback" in result["degradation_flags"]

    def test_model_uses_input_features(self, agent: MLExecutorAgent, valid_input: PredictionInput) -> None:
        result = agent.execute(valid_input, model_version="v1.2.0")
        fi = result["feature_importance"]
        assert "soil_moisture" in fi
        assert "temperature_c" in fi
        assert "rainfall_mm" in fi
        assert all(0.0 <= v <= 1.0 for v in fi.values())
