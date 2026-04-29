from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.predictions.agents.data_analyst import DataAnalystAgent
from backend.predictions.agents.explainability import ExplainabilityAgent
from backend.predictions.agents.ml_executor import MLExecutorAgent
from backend.predictions.agents.reviewer import ReviewerAgent
from backend.predictions.graph import PredictionGraph
from backend.predictions.models import PredictionInput, PredictionStatus


class TestGracefulDegradation:
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

    def test_ml_executor_fallback(self, valid_input: PredictionInput) -> None:
        # Mock ml_executor to fail on first call, succeed on fallback
        ml_mock = MagicMock(spec=MLExecutorAgent)
        ml_mock.execute.side_effect = Exception("Primary model unavailable")
        ml_mock.execute_with_fallback.return_value = {
            "prediction": 7.5,
            "confidence_interval": {"lower": 5.0, "upper": 10.0},
            "feature_importance": {"soil_moisture": 0.65, "temperature_c": 0.35},
            "model_version": "cached",
            "status": "degraded",
            "degradation_flags": ["cached_model_fallback"],
            "staleness_warning": True,
        }

        graph = PredictionGraph(ml_executor=ml_mock)
        result = graph.execute(valid_input, model_version="v1.2.0")

        assert result.status == PredictionStatus.DEGRADED  # degraded but still useful
        assert "cached_model_fallback" in result.degradation_flags
        ml_mock.execute_with_fallback.assert_called_once()

    def test_explainability_failure_continues(self, valid_input: PredictionInput) -> None:
        # Mock explainability to fail
        expl_mock = MagicMock(spec=ExplainabilityAgent)
        expl_mock.execute.side_effect = Exception("Explainability service timeout")

        graph = PredictionGraph(explainability=expl_mock)
        result = graph.execute(valid_input, model_version="v1.2.0")

        assert result.status == PredictionStatus.DEGRADED
        assert "explainability_failure" in result.degradation_flags
        assert result.explanation_artifact is None

    def test_reviewer_failure_escalates(self, valid_input: PredictionInput) -> None:
        # Mock reviewer to fail
        review_mock = MagicMock(spec=ReviewerAgent)
        review_mock.execute.side_effect = Exception("Policy check failed")

        graph = PredictionGraph(reviewer=review_mock)
        result = graph.execute(valid_input, model_version="v1.2.0")

        assert result.status == PredictionStatus.ESCALATED
        assert result.escalation_reason is not None
        assert "Policy check failed" in result.escalation_reason

    def test_unrecoverable_ml_failure_escalates(self, valid_input: PredictionInput) -> None:
        # Mock ml_executor to fail even on fallback
        ml_mock = MagicMock(spec=MLExecutorAgent)
        ml_mock.execute.side_effect = Exception("Primary model unavailable")
        ml_mock.execute_with_fallback.side_effect = Exception("Cached model also unavailable")

        graph = PredictionGraph(ml_executor=ml_mock)
        result = graph.execute(valid_input, model_version="v1.2.0")

        assert result.status == PredictionStatus.ESCALATED
        assert "Cached model also unavailable" in result.escalation_reason

    def test_data_analyst_failure_escalates(self, valid_input: PredictionInput) -> None:
        # Mock data_analyst to fail
        da_mock = MagicMock(spec=DataAnalystAgent)
        da_mock.execute.side_effect = Exception("Validation pipeline crashed")

        graph = PredictionGraph(data_analyst=da_mock)
        result = graph.execute(valid_input, model_version="v1.2.0")

        assert result.status == PredictionStatus.ESCALATED
        assert "Validation pipeline crashed" in result.escalation_reason
