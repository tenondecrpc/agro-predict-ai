from __future__ import annotations

from typing import Any

from backend.predictions.models import PredictionInput


class ExplainabilityAgent:
    """Produces explanation artifacts for predictions.

    Generates:
    - Feature importance scores
    - Data sources used with validation status
    - Confidence level computation
    - Uncertainty factor identification
    - Human-readable summary
    """

    def execute(
        self,
        input_data: PredictionInput,
        ml_result: dict[str, Any],
        analyst_result: dict[str, Any],
    ) -> dict[str, Any]:
        feature_scores = dict(ml_result.get("feature_importance", {}))
        data_sources_used = self._extract_data_sources(analyst_result)
        confidence_level = self._compute_confidence(ml_result, analyst_result)
        uncertainty_factors = self._identify_uncertainty_factors(ml_result, analyst_result, confidence_level)
        human_readable_summary = self._build_summary(
            input_data.crop,
            input_data.region,
            ml_result,
            feature_scores,
            confidence_level,
            uncertainty_factors,
        )

        return {
            "feature_scores": feature_scores,
            "data_sources_used": data_sources_used,
            "confidence_level": round(confidence_level, 3),
            "uncertainty_factors": uncertainty_factors,
            "human_readable_summary": human_readable_summary,
        }

    def _extract_data_sources(self, analyst_result: dict[str, Any]) -> list[str]:
        sources = analyst_result.get("data_sources", [])
        return [s["source_id"] for s in sources if s.get("validation_status") == "passed"]

    def _compute_confidence(
        self,
        ml_result: dict[str, Any],
        analyst_result: dict[str, Any],
    ) -> float:
        confidence_interval = ml_result.get("confidence_interval", {})
        prediction = float(ml_result.get("prediction", 1.0))
        lower = confidence_interval.get("lower", prediction)
        upper = confidence_interval.get("upper", prediction)

        if prediction <= 0:
            return 0.5

        ci_width = upper - lower
        relative_width = ci_width / prediction

        # Base confidence from CI width (narrower = higher confidence)
        if relative_width < 0.15:
            base_confidence = 0.95
        elif relative_width < 0.25:
            base_confidence = 0.85
        elif relative_width < 0.40:
            base_confidence = 0.70
        else:
            base_confidence = 0.55

        # Adjust for data quality issues
        if analyst_result.get("uncertainty_flagged", False):
            base_confidence *= 0.85

        # Adjust for cached model
        if ml_result.get("staleness_warning", False):
            base_confidence *= 0.80

        return max(0.0, min(1.0, base_confidence))

    def _identify_uncertainty_factors(
        self,
        ml_result: dict[str, Any],
        analyst_result: dict[str, Any],
        confidence_level: float,
    ) -> list[str]:
        factors = []

        confidence_interval = ml_result.get("confidence_interval", {})
        prediction = float(ml_result.get("prediction", 1.0))
        lower = confidence_interval.get("lower", prediction)
        upper = confidence_interval.get("upper", prediction)
        relative_width = (upper - lower) / prediction if prediction > 0 else 1.0

        if relative_width > 0.40:
            factors.append("wide_confidence_interval")
        elif relative_width > 0.25:
            factors.append("moderate_confidence_interval")

        if analyst_result.get("uncertainty_flagged", False):
            reasons = analyst_result.get("uncertainty_reasons", [])
            factors.extend(reasons)

        if ml_result.get("staleness_warning", False):
            factors.append("cached_model_fallback")


        # If confidence is low, identify top contributing feature uncertainty
        feature_importance = ml_result.get("feature_importance", {})
        if confidence_level < 0.7 and feature_importance:
            top_feature = max(feature_importance, key=feature_importance.get)
            factors.append(f"high_variance_in_{top_feature}")

        return factors

    def _build_summary(
        self,
        crop: str,
        region: str,
        ml_result: dict[str, Any],
        feature_scores: dict[str, float],
        confidence_level: float,
        uncertainty_factors: list[str],
    ) -> str:
        prediction = ml_result.get("prediction", "N/A")
        parts = [f"Yield prediction for {crop} in {region}: {prediction} tons/hectare."]

        if feature_scores:
            top_feature = max(feature_scores, key=feature_scores.get)
            top_score = feature_scores[top_feature]
            parts.append(f"Primary driver: {top_feature} (importance: {top_score:.0%}).")

        parts.append(f"Model confidence: {confidence_level:.0%}.")

        if uncertainty_factors:
            parts.append(f"Uncertainty sources: {', '.join(uncertainty_factors)}.")
        else:
            parts.append("All data quality checks passed with no significant uncertainty.")

        return " ".join(parts)
