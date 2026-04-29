"""ML model adapter layer for AgroPredict AI.

Provides a Protocol-based adapter interface so the prediction pipeline can swap
between scikit-learn models, deep-learning frameworks, and a formula fallback
without changing the calling code.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)

_FEATURE_NAMES = ["soil_moisture", "temperature_c", "rainfall_mm"]


@dataclass
class ModelPrediction:
    """Output from any MLModelAdapter implementation."""

    point_estimate: float
    confidence_interval: dict[str, float]
    feature_importance: dict[str, float]
    model_version: str
    ood_flags: list[str] = field(default_factory=list)


@runtime_checkable
class MLModelAdapter(Protocol):
    """Protocol for all ML model adapters."""

    def predict(self, features: dict[str, float]) -> ModelPrediction: ...


class ScikitLearnAdapter:
    """Loads a joblib-serialised scikit-learn model and wraps it as an MLModelAdapter.

    - Uses per-tree variance (std across tree predictions) for the confidence interval.
    - Detects out-of-distribution features via p1/p99 quantiles from training.
    - Reads metadata from the companion _metadata.json file when present.
    """

    def __init__(self, model_path: str) -> None:
        import joblib

        self._model_path = Path(model_path)
        if not self._model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        self._model = joblib.load(self._model_path)
        self._metadata = self._load_metadata()
        self._model_version = self._metadata.get("version", "v1.0.0")
        self._p1_quantiles: dict[str, float] = self._metadata.get("p1_quantiles", {})
        self._p99_quantiles: dict[str, float] = self._metadata.get("p99_quantiles", {})
        self._feature_names: list[str] = self._metadata.get("feature_names", _FEATURE_NAMES)

        logger.info(
            "ml_model_loaded",
            extra={
                "model_path": str(self._model_path),
                "version": self._model_version,
                "r2": self._metadata.get("r2"),
            },
        )

    def _load_metadata(self) -> dict:
        stem_parts = self._model_path.stem  # e.g. corn_rf_v1.0.0_abcd1234
        # Try standard companion name first
        meta_candidates = [
            self._model_path.parent / "corn_rf_v1.0.0_metadata.json",
            self._model_path.with_suffix(".json"),
            self._model_path.parent / f"{stem_parts}_metadata.json",
        ]
        for candidate in meta_candidates:
            if candidate.exists():
                with open(candidate) as f:
                    return json.load(f)
        return {}

    def predict(self, features: dict[str, float]) -> ModelPrediction:
        import numpy as np

        feature_vector = np.array([[features.get(name, 0.0) for name in self._feature_names]])

        # OOD detection
        ood_flags: list[str] = []
        for name in self._feature_names:
            val = features.get(name)
            if val is None:
                ood_flags.append(f"missing_feature:{name}")
                continue
            p1 = self._p1_quantiles.get(name)
            p99 = self._p99_quantiles.get(name)
            if p1 is not None and p99 is not None:
                if val < p1 or val > p99:
                    ood_flags.append(f"ood:{name}")

        # Point estimate
        point_estimate = float(self._model.predict(feature_vector)[0])

        # Confidence interval via per-tree variance
        tree_preds = np.array([tree.predict(feature_vector)[0] for tree in self._model.estimators_])
        std = float(np.std(tree_preds))
        ci = {
            "lower": round(point_estimate - 1.96 * std, 4),
            "upper": round(point_estimate + 1.96 * std, 4),
        }

        # Feature importance from the model
        importances = self._model.feature_importances_
        feature_importance = {
            name: round(float(importances[i]), 4)
            for i, name in enumerate(self._feature_names)
        }

        return ModelPrediction(
            point_estimate=round(point_estimate, 4),
            confidence_interval=ci,
            feature_importance=feature_importance,
            model_version=self._model_version,
            ood_flags=ood_flags,
        )


class FormulaFallbackAdapter:
    """Deterministic formula-based fallback adapter.

    Keeps the original formula so predictions remain available when no model file
    is present. Always includes the 'model_file_missing' degradation flag in the
    ood_flags list so callers can propagate the flag.
    """

    def __init__(self, version: str = "formula_fallback") -> None:
        self._version = version

    def predict(self, features: dict[str, float]) -> ModelPrediction:
        soil = features.get("soil_moisture", 0.3)
        temp = features.get("temperature_c", 20.0)
        rain = features.get("rainfall_mm", 40.0)

        point_estimate = 3.0 + soil * 8.0 + temp * 0.12 + rain * 0.025
        uncertainty = max(0.5, 1.5 - soil * 2.0)

        ci = {
            "lower": round(point_estimate - uncertainty, 4),
            "upper": round(point_estimate + uncertainty, 4),
        }

        raw_importance = {
            "soil_moisture": soil * 8.0,
            "temperature_c": temp * 0.12,
            "rainfall_mm": rain * 0.025,
        }
        total = sum(raw_importance.values()) or 1.0
        feature_importance = {k: round(v / total, 4) for k, v in raw_importance.items()}

        return ModelPrediction(
            point_estimate=round(point_estimate, 4),
            confidence_interval=ci,
            feature_importance=feature_importance,
            model_version=self._version,
            ood_flags=["model_file_missing"],
        )


def build_adapter_from_env() -> MLModelAdapter:
    """Build the appropriate adapter based on environment configuration.

    Checks ML_MODEL_PATH env var. If the file exists, returns a ScikitLearnAdapter.
    Otherwise falls back to FormulaFallbackAdapter.
    """
    import os

    model_path = os.getenv("ML_MODEL_PATH", "")
    if model_path and Path(model_path).exists():
        try:
            return ScikitLearnAdapter(model_path)
        except Exception as exc:
            logger.warning(
                "ml_model_load_failed_using_fallback",
                extra={"model_path": model_path, "error": str(exc)},
            )
    return FormulaFallbackAdapter()
