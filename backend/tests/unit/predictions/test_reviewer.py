from __future__ import annotations

import pytest

from backend.predictions.agents.reviewer import PolicyViolationError, ReviewerAgent
from backend.predictions.models import PredictionInput


class TestReviewerAgent:
    @pytest.fixture
    def agent(self) -> ReviewerAgent:
        return ReviewerAgent()

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

    def test_approves_complete_prediction(self, agent: ReviewerAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 8.5,
            "confidence_interval": {"lower": 7.2, "upper": 9.8},
            "feature_importance": {"soil_moisture": 0.45},
            "model_version": "v1.2.0",
            "status": "success",
        }
        explainability_result = {
            "feature_scores": {"soil_moisture": 0.45},
            "data_sources_used": ["weather-001"],
            "confidence_level": 0.85,
            "uncertainty_factors": [],
            "human_readable_summary": "Good yield expected.",
        }
        recommendation_result = {
            "recommendation": "Maintain current practices.",
            "priority": "low",
            "actions": ["Monitor"],
        }
        result = agent.execute(valid_input, ml_result, explainability_result, recommendation_result)
        assert result["approved"] is True
        assert result["review_status"] == "approved"
        assert "reviewer_notes" in result

    def test_rejects_missing_explanation(
        self, agent: ReviewerAgent, valid_input: PredictionInput
    ) -> None:
        ml_result = {
            "prediction": 8.5,
            "confidence_interval": {"lower": 7.2, "upper": 9.8},
            "feature_importance": {},
            "model_version": "v1.2.0",
        }
        explainability_result = {
            "feature_scores": {},
            "data_sources_used": [],
            "confidence_level": 0.85,
            "uncertainty_factors": [],
            "human_readable_summary": "",
        }
        recommendation_result = {"recommendation": "", "priority": "low", "actions": []}
        with pytest.raises(PolicyViolationError) as exc_info:
            agent.execute(valid_input, ml_result, explainability_result, recommendation_result)
        assert "explanation" in str(exc_info.value).lower()
        assert exc_info.value.violation_type == "missing_explanation"

    def test_rejects_missing_provenance(
        self, agent: ReviewerAgent, valid_input: PredictionInput
    ) -> None:
        ml_result = {
            "prediction": 8.5,
            "confidence_interval": {"lower": 7.2, "upper": 9.8},
            "feature_importance": {},
            "model_version": "v1.2.0",
        }
        explainability_result = {
            "feature_scores": {"soil_moisture": 0.45},
            "data_sources_used": [],  # No provenance
            "confidence_level": 0.85,
            "uncertainty_factors": [],
            "human_readable_summary": "Good yield.",
        }
        recommendation_result = {"recommendation": "Maintain.", "priority": "low", "actions": ["Monitor"]}
        with pytest.raises(PolicyViolationError) as exc_info:
            agent.execute(valid_input, ml_result, explainability_result, recommendation_result)
        assert "provenance" in str(exc_info.value).lower()

    def test_rejects_low_confidence_without_uncertainty_acknowledgment(
        self, agent: ReviewerAgent, valid_input: PredictionInput
    ) -> None:
        ml_result = {
            "prediction": 6.0,
            "confidence_interval": {"lower": 3.0, "upper": 9.0},
            "feature_importance": {},
            "model_version": "v1.2.0",
        }
        explainability_result = {
            "feature_scores": {},
            "data_sources_used": ["weather-001"],
            "confidence_level": 0.55,
            "uncertainty_factors": [],  # Should have factors for low confidence
            "human_readable_summary": "Uncertain.",
        }
        recommendation_result = {"recommendation": "Caution.", "priority": "high", "actions": ["Check"]}
        with pytest.raises(PolicyViolationError) as exc_info:
            agent.execute(valid_input, ml_result, explainability_result, recommendation_result)
        assert "uncertainty" in str(exc_info.value).lower()

    def test_approves_degraded_with_explicit_flags(self, agent: ReviewerAgent, valid_input: PredictionInput) -> None:
        ml_result = {
            "prediction": 6.0,
            "confidence_interval": {"lower": 4.0, "upper": 8.0},
            "feature_importance": {},
            "model_version": "cached",
            "staleness_warning": True,
            "degradation_flags": ["cached_model_fallback"],
            "status": "degraded",
        }
        explainability_result = {
            "feature_scores": {},
            "data_sources_used": ["weather-001"],
            "confidence_level": 0.60,
            "uncertainty_factors": ["cached_model_fallback", "wide_confidence_interval"],
            "human_readable_summary": "Degraded prediction.",
        }
        recommendation_result = {
            "recommendation": "Caution: degraded data.",
            "priority": "high",
            "actions": ["Verify"],
            "degraded": True,
        }
        result = agent.execute(valid_input, ml_result, explainability_result, recommendation_result)
        assert result["approved"] is True
        assert result["review_status"] == "approved_with_caution"
        assert result["degraded"] is True
