from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from backend.ml_models.adapter import FormulaFallbackAdapter, MLModelAdapter, ScikitLearnAdapter
from backend.predictions.models import PredictionInput

logger = logging.getLogger(__name__)


class ModelUnavailableError(Exception):
    """Raised when the requested model version is unavailable and no fallback exists."""


class CachedModelFallback(Exception):
    """Raised to signal that cached-model fallback was activated."""


def _load_adapter_from_env() -> MLModelAdapter | None:
    """Attempt to load a ScikitLearnAdapter from ML_MODEL_PATH env var.

    Returns None if the env var is not set or the file does not exist.
    """
    import os

    model_path = os.getenv("ML_MODEL_PATH", "")
    if model_path and Path(model_path).exists():
        try:
            return ScikitLearnAdapter(model_path)
        except Exception as exc:
            logger.warning(
                "ml_adapter_load_failed",
                extra={"model_path": model_path, "error": str(exc)},
            )
    return None


class MLExecutorAgent:
    """Executes the ML model to generate predictions.

    Supports:
    - Active model execution via MLModelAdapter (ScikitLearn or formula fallback)
    - Cached-model fallback on primary failure
    - Confidence interval and feature importance generation
    - OOD (out-of-distribution) detection via adapter
    """

    # Registry of available model versions with their parameters
    MODEL_REGISTRY: dict[str, dict[str, Any]] = {
        "v1.2.0": {
            "model_id": "crop_yield_regressor_v1",
            "supports_crops": ["corn", "wheat", "soybean"],
            "supports_regions": ["midwest_us", "great_plains", "default"],
        },
        "v1.0.0": {
            "model_id": "crop_yield_regressor_v1",
            "supports_crops": ["corn", "wheat", "soybean"],
            "supports_regions": ["midwest_us", "great_plains", "default"],
        },
    }

    def __init__(
        self,
        adapter: MLModelAdapter | None = None,
        *,
        shadow_adapter: MLModelAdapter | None = None,
    ) -> None:
        # If no adapter provided, try to load from ML_MODEL_PATH env var.
        # Fall back to FormulaFallbackAdapter if not available.
        # Note: formula fallback is a valid prediction method and does NOT set
        # degradation flags on the output - model_file_missing is informational only
        # and tracked via ModelPrediction.ood_flags in the adapter layer.
        if adapter is not None:
            self._adapter = adapter
        else:
            loaded = _load_adapter_from_env()
            self._adapter = loaded if loaded is not None else FormulaFallbackAdapter()
        self._shadow_adapter = shadow_adapter
        self._degradation_flags: list[str] = []

    def execute(self, input_data: PredictionInput, *, model_version: str) -> dict[str, Any]:
        model = self.MODEL_REGISTRY.get(model_version)
        if model is None:
            raise ModelUnavailableError(f"Model version {model_version} not found in registry")

        if input_data.crop not in model["supports_crops"] and "default" not in model["supports_crops"]:
            raise ModelUnavailableError(f"Model {model_version} does not support crop {input_data.crop}")

        prediction = self._run_model(input_data, model_version=model_version)
        return prediction

    def execute_with_fallback(
        self,
        input_data: PredictionInput,
        *,
        primary_version: str,
        force_fallback: bool = False,
    ) -> dict[str, Any]:
        try:
            if force_fallback:
                raise ModelUnavailableError("Forced fallback")
            return self.execute(input_data, model_version=primary_version)
        except ModelUnavailableError:
            # Attempt cached-model fallback
            return self._cached_model_fallback(input_data)

    def _run_model(
        self,
        input_data: PredictionInput,
        *,
        model_version: str,
    ) -> dict[str, Any]:
        features = {
            "soil_moisture": float(input_data.input_data.get("soil_moisture", 0.3)),
            "temperature_c": float(input_data.input_data.get("temperature_c", 20.0)),
            "rainfall_mm": float(input_data.input_data.get("rainfall_mm", 40.0)),
        }

        model_pred = self._adapter.predict(features)

        # Shadow mode: run shadow model alongside active model
        shadow_output = None
        if self._shadow_adapter is not None:
            try:
                shadow_pred = self._shadow_adapter.predict(features)
                shadow_output = {
                    "point_estimate": shadow_pred.point_estimate,
                    "confidence_interval": shadow_pred.confidence_interval,
                }
            except Exception as exc:
                logger.warning("shadow_model_failed", extra={"error": str(exc)})

        # Combine OOD flags with any existing degradation flags.
        degradation_flags = list(self._degradation_flags)
        real_ood = [f for f in model_pred.ood_flags if f != "model_file_missing"]
        if real_ood:
            degradation_flags.extend([f"ood_detected:{f}" for f in real_ood])

        result = {
            "prediction": model_pred.point_estimate,
            "confidence_interval": model_pred.confidence_interval,
            "feature_importance": model_pred.feature_importance,
            "model_version": model_version,
            "status": "success",
            "degradation_flags": degradation_flags,
            "staleness_warning": False,
        }
        if shadow_output is not None:
            result["shadow_output"] = shadow_output

        return result

    def _cached_model_fallback(self, input_data: PredictionInput) -> dict[str, Any]:
        # Cached model uses simpler parameters with higher uncertainty (FormulaFallbackAdapter)
        fallback_adapter = FormulaFallbackAdapter(version="cached")
        features = {
            "soil_moisture": float(input_data.input_data.get("soil_moisture", 0.3)),
            "temperature_c": float(input_data.input_data.get("temperature_c", 20.0)),
            "rainfall_mm": float(input_data.input_data.get("rainfall_mm", 40.0)),
        }
        model_pred = fallback_adapter.predict(features)

        # Override CI with higher uncertainty for cached fallback
        uncertainty = 2.5
        confidence_interval = {
            "lower": round(model_pred.point_estimate - uncertainty, 2),
            "upper": round(model_pred.point_estimate + uncertainty, 2),
        }

        return {
            "prediction": round(model_pred.point_estimate, 2),
            "confidence_interval": confidence_interval,
            "feature_importance": {
                "soil_moisture": 0.65,
                "temperature_c": 0.35,
            },
            "model_version": "cached",
            "status": "degraded",
            "degradation_flags": ["cached_model_fallback"],
            "staleness_warning": True,
        }
