from __future__ import annotations

import json
import logging
from typing import Any

from backend.predictions.models import PredictionInput

logger = logging.getLogger(__name__)


class RecommendationEngineAgent:
    """Generates actionable recommendations based on model predictions.

    When an LLM adapter is provided and LLM is enabled, uses the LLM to generate
    richer, context-aware recommendations. Falls back to deterministic logic on
    any LLM failure.
    """

    def __init__(self, llm_adapter: Any = None) -> None:
        self._llm_adapter = llm_adapter

    def execute(
        self,
        input_data: PredictionInput,
        ml_result: dict[str, Any],
    ) -> dict[str, Any]:
        prediction = float(ml_result.get("prediction", 0.0))
        confidence_interval = ml_result.get("confidence_interval", {})
        feature_importance = ml_result.get("feature_importance", {})
        is_degraded = ml_result.get("staleness_warning", False) or bool(ml_result.get("degradation_flags", []))

        # Try LLM path if adapter available
        if self._llm_adapter is not None:
            try:
                llm_result = self._execute_llm(input_data, ml_result)
                if llm_result is not None:
                    return llm_result
            except Exception as exc:
                logger.warning(
                    "llm_recommendation_failed_using_fallback",
                    extra={"error": str(exc)},
                )

        # Deterministic fallback
        priority = self._determine_priority(prediction, confidence_interval)
        recommendation = self._build_recommendation(
            input_data.crop,
            input_data.region,
            prediction,
            priority,
            is_degraded,
        )
        actions = self._build_actions(
            input_data.crop,
            prediction,
            priority,
            feature_importance,
            is_degraded,
        )

        return {
            "recommendation": recommendation,
            "priority": priority,
            "actions": actions,
            "degraded": is_degraded,
            "prediction_value": prediction,
        }

    def _execute_llm(
        self,
        input_data: PredictionInput,
        ml_result: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Call the LLM adapter and parse the JSON response.

        Returns None if parsing fails so the caller falls back to deterministic logic.
        """
        system = (
            "You are an agricultural AI assistant. Given crop prediction data, "
            "generate a JSON object with keys: recommendation (str), priority (str: high|medium|low), "
            "actions (list[str]). Respond ONLY with valid JSON."
        )
        prompt = (
            f"Crop: {input_data.crop}\n"
            f"Region: {input_data.region}\n"
            f"Predicted yield: {ml_result.get('prediction')} tons/ha\n"
            f"Confidence interval: {ml_result.get('confidence_interval')}\n"
            f"Feature importance: {ml_result.get('feature_importance')}\n"
            "Generate a farming recommendation."
        )

        raw = self._llm_adapter.complete(prompt, system)
        if not raw:
            return None

        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("LLM returned non-dict JSON")
            recommendation = str(parsed.get("recommendation", ""))
            priority = str(parsed.get("priority", "medium"))
            actions = list(parsed.get("actions", []))
            is_degraded = ml_result.get("staleness_warning", False) or bool(ml_result.get("degradation_flags", []))
            return {
                "recommendation": recommendation,
                "priority": priority,
                "actions": actions,
                "degraded": is_degraded,
                "prediction_value": float(ml_result.get("prediction", 0.0)),
            }
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "llm_recommendation_parse_failed",
                extra={"error": str(exc), "raw_response": raw[:200]},
            )
            return None

    def _determine_priority(
        self,
        prediction: float,
        confidence_interval: dict[str, float],
    ) -> str:
        lower = confidence_interval.get("lower", prediction)
        upper = confidence_interval.get("upper", prediction)
        ci_width = upper - lower
        relative_uncertainty = ci_width / prediction if prediction > 0 else 1.0

        if prediction < 5.0 or relative_uncertainty > 0.4:
            return "high"
        elif prediction < 8.0 or relative_uncertainty > 0.25:
            return "medium"
        return "low"

    def _build_recommendation(
        self,
        crop: str,
        region: str,
        prediction: float,
        priority: str,
        is_degraded: bool,
    ) -> str:
        parts = [f"For {crop} in {region}:", f"predicted yield is {prediction} tons per hectare."]

        if priority == "high":
            parts.append("Immediate attention recommended.")
        elif priority == "medium":
            parts.append("Monitor conditions closely.")
        else:
            parts.append("Maintain current practices.")

        if is_degraded:
            parts.append("CAUTION: This recommendation is based on cached/stale model data. Verify before acting.")

        return " ".join(parts)

    def _build_actions(
        self,
        crop: str,
        prediction: float,
        priority: str,
        feature_importance: dict[str, float],
        is_degraded: bool,
    ) -> list[str]:
        actions = []

        if priority == "high":
            actions.append(f"Schedule irrigation assessment for {crop}")
            actions.append("Review soil nutrient levels within 48 hours")
        elif priority == "medium":
            actions.append(f"Continue standard monitoring for {crop}")
            actions.append("Prepare contingency irrigation plan")
        else:
            actions.append(f"Maintain current irrigation schedule for {crop}")

        top_feature = max(feature_importance, key=feature_importance.get, default="")
        if top_feature == "soil_moisture":
            actions.append("Calibrate soil moisture sensors")
        elif top_feature == "temperature_c":
            actions.append("Review heat stress mitigation strategies")
        elif top_feature == "rainfall_mm":
            actions.append("Check drainage systems")

        if is_degraded:
            actions.append("Re-run prediction with fresh data when connectivity is restored")

        return actions
