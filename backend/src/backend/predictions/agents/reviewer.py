from __future__ import annotations

import json
import logging
from typing import Any

from backend.predictions.models import PredictionInput

logger = logging.getLogger(__name__)


class PolicyViolationError(Exception):
    def __init__(self, message: str, *, violation_type: str) -> None:
        super().__init__(message)
        self.violation_type = violation_type


class ReviewerAgent:
    """Validates prediction output completeness and policy compliance.

    Enforces:
    - Explanation artifacts must be present and non-empty
    - Data provenance chain must exist
    - Low-confidence predictions must acknowledge uncertainty
    - Degraded predictions must have explicit flags

    When an LLM adapter is provided and LLM is enabled, augments the review
    with LLM reasoning. Falls back to rule-based review on any LLM failure.
    """

    MIN_CONFIDENCE_THRESHOLD = 0.70

    def __init__(self, llm_adapter: Any = None) -> None:
        self._llm_adapter = llm_adapter

    def execute(
        self,
        input_data: PredictionInput,
        ml_result: dict[str, Any],
        explainability_result: dict[str, Any],
        recommendation_result: dict[str, Any],
    ) -> dict[str, Any]:
        # Rule-based checks always run (mandatory policy gates)
        self._run_mandatory_checks(ml_result, explainability_result)

        # Try LLM augmentation if adapter available
        if self._llm_adapter is not None:
            try:
                llm_review = self._execute_llm(ml_result, explainability_result, recommendation_result)
                if llm_review is not None:
                    return llm_review
            except Exception as exc:
                logger.warning(
                    "llm_review_failed_using_fallback",
                    extra={"error": str(exc)},
                )

        # Deterministic fallback
        return self._build_deterministic_review(ml_result, explainability_result, recommendation_result)

    def _run_mandatory_checks(
        self,
        ml_result: dict[str, Any],
        explainability_result: dict[str, Any],
    ) -> None:
        """Always-run policy gate checks. Raises PolicyViolationError on failure."""
        if not explainability_result.get("human_readable_summary"):
            raise PolicyViolationError(
                "Prediction rejected: explanation artifact is missing or empty",
                violation_type="missing_explanation",
            )

        if not explainability_result.get("data_sources_used"):
            raise PolicyViolationError(
                "Prediction rejected: data provenance chain is missing",
                violation_type="missing_provenance",
            )

        confidence_level = float(explainability_result.get("confidence_level", 1.0))
        uncertainty_factors = explainability_result.get("uncertainty_factors", [])
        if confidence_level < self.MIN_CONFIDENCE_THRESHOLD and not uncertainty_factors:
            raise PolicyViolationError(
                f"Prediction rejected: confidence {confidence_level:.0%} below threshold "
                f"but no uncertainty factors documented",
                violation_type="missing_uncertainty_acknowledgment",
            )

        is_degraded = ml_result.get("staleness_warning", False) or bool(ml_result.get("degradation_flags", []))
        if is_degraded and not uncertainty_factors:
            raise PolicyViolationError(
                "Prediction rejected: degraded prediction missing uncertainty documentation",
                violation_type="missing_degradation_acknowledgment",
            )

    def _execute_llm(
        self,
        ml_result: dict[str, Any],
        explainability_result: dict[str, Any],
        recommendation_result: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Call the LLM adapter for review augmentation."""
        system = (
            "You are a senior agronomist reviewing an AI prediction. "
            "Given the prediction data, return a JSON object with keys: "
            "approved (bool), reason (str), notes (str). Respond ONLY with valid JSON."
        )
        prompt = (
            f"ML result: {json.dumps(ml_result)}\n"
            f"Explanation: {json.dumps(explainability_result)}\n"
            f"Recommendation: {json.dumps(recommendation_result)}\n"
            "Please review this prediction and provide your assessment."
        )

        raw = self._llm_adapter.complete(prompt, system)
        if not raw:
            return None

        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("LLM returned non-dict JSON")
            is_degraded = ml_result.get("staleness_warning", False) or bool(ml_result.get("degradation_flags", []))
            confidence_level = float(explainability_result.get("confidence_level", 1.0))
            is_cautious = is_degraded or confidence_level < self.MIN_CONFIDENCE_THRESHOLD
            status = "approved_with_caution" if is_cautious else "approved"
            return {
                "approved": bool(parsed.get("approved", True)),
                "review_status": status,
                "reviewer_notes": str(parsed.get("notes", "")),
                "degraded": is_degraded,
                "confidence_level_at_review": confidence_level,
            }
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "llm_review_parse_failed",
                extra={"error": str(exc)},
            )
            return None

    def _build_deterministic_review(
        self,
        ml_result: dict[str, Any],
        explainability_result: dict[str, Any],
        recommendation_result: dict[str, Any],
    ) -> dict[str, Any]:
        confidence_level = float(explainability_result.get("confidence_level", 1.0))
        uncertainty_factors = explainability_result.get("uncertainty_factors", [])
        is_degraded = ml_result.get("staleness_warning", False) or bool(ml_result.get("degradation_flags", []))

        notes = self._build_notes(
            confidence_level,
            uncertainty_factors,
            is_degraded,
            recommendation_result.get("priority", "low"),
        )

        if is_degraded or confidence_level < self.MIN_CONFIDENCE_THRESHOLD:
            status = "approved_with_caution"
        else:
            status = "approved"

        return {
            "approved": True,
            "review_status": status,
            "reviewer_notes": notes,
            "degraded": is_degraded,
            "confidence_level_at_review": confidence_level,
        }

    def _build_notes(
        self,
        confidence_level: float,
        uncertainty_factors: list[str],
        is_degraded: bool,
        priority: str,
    ) -> str:
        parts = ["Review complete."]

        if is_degraded:
            parts.append("CAUTION: Prediction was generated using degraded/cached model data.")

        if confidence_level < self.MIN_CONFIDENCE_THRESHOLD:
            parts.append(f"Confidence is low ({confidence_level:.0%}). Recommend verification.")

        if uncertainty_factors:
            parts.append(f"Documented uncertainty: {', '.join(uncertainty_factors)}.")

        if priority == "high":
            parts.append("High priority actions identified - expedite review with agronomist.")

        return " ".join(parts)
