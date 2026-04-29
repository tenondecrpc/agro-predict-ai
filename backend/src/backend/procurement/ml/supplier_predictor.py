"""Supplier performance predictor.

Wraps a scikit-learn ``GradientBoostingClassifier`` (same family as
XGBoost; it is what the platform already ships). Inference can run
either with the trained model on disk or with a deterministic feature-
based fallback so the demo always produces a reasonable score.

Outputs ``SupplierPrediction``: probability that the supplier delivers
on time, expected delay in days when late, and a confidence band
derived from the number of historical observations.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import joblib

from backend.procurement.ml.features import (
    FEATURE_NAMES,
    SupplierFeatures,
    SupplierPerformanceRecord,
    extract_features,
    to_vector,
)
from backend.procurement.ml.models import SupplierPrediction

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = Path("backend/models/procurement_supplier_predictor_v1.joblib")
MODEL_VERSION_FALLBACK = "rules-v1"
MODEL_VERSION_TRAINED = "gbm-v1"
MODEL_PATH_ENV = "BACKEND_PROCUREMENT_SUPPLIER_MODEL_PATH"


def _confidence_band(n_observations: int) -> str:
    if n_observations >= 12:
        return "high"
    if n_observations >= 4:
        return "medium"
    return "low"


def _rules_based_p_on_time(features: SupplierFeatures) -> float:
    """Deterministic fallback for when no trained model is available.

    Heuristic: weighted blend of recent and overall on-time rates.
    Penalize average delay for late deliveries. Bound to [0.05, 0.99].
    """

    if features.n_observations == 0:
        return 0.65  # industry average for LATAM agro procurement
    base = (
        0.50 * features.on_time_rate_last_3
        + 0.30 * features.on_time_rate_last_6
        + 0.20 * features.on_time_rate_all
    )
    # Penalty for chronic delay: more than 5 days average delay drags 10 points
    penalty = min(0.20, max(0.0, (features.avg_delay_days - 2.0) * 0.04))
    p = max(0.05, min(0.99, base - penalty))
    return p


def _top_features_from_features(features: SupplierFeatures) -> list[str]:
    drivers: list[tuple[str, float]] = [
        ("on_time_rate_last_3", features.on_time_rate_last_3),
        ("on_time_rate_last_6", features.on_time_rate_last_6),
        ("on_time_rate_all", features.on_time_rate_all),
        ("avg_delay_days", -features.avg_delay_days / 10.0),
        ("category_consistency", features.category_consistency),
    ]
    drivers.sort(key=lambda x: abs(x[1]), reverse=True)
    return [name for name, _ in drivers[:3]]


class SupplierPredictor:
    """Loads a trained classifier on demand; falls back to rules."""

    def __init__(self, model_path: Path | None = None) -> None:
        env_path = os.environ.get(MODEL_PATH_ENV)
        self._model_path = Path(env_path) if env_path else (model_path or DEFAULT_MODEL_PATH)
        self._model: Any | None = None
        self._tried_load = False

    def _ensure_loaded(self) -> None:
        if self._tried_load:
            return
        self._tried_load = True
        if not self._model_path.exists():
            logger.info(
                "supplier_predictor model not found at %s; using rules-based fallback",
                self._model_path,
            )
            return
        try:
            self._model = joblib.load(self._model_path)
        except Exception:
            logger.exception("failed to load supplier_predictor model from %s", self._model_path)
            self._model = None

    @property
    def is_trained(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    def predict_for_supplier(
        self,
        supplier_id: str,
        history: list[SupplierPerformanceRecord],
    ) -> SupplierPrediction:
        features = extract_features(supplier_id, history)
        return self.predict_for_features(features)

    def predict_for_features(self, features: SupplierFeatures) -> SupplierPrediction:
        self._ensure_loaded()
        if self._model is not None:
            vec = [to_vector(features)]
            try:
                p_on_time = float(self._model.predict_proba(vec)[0][1])
                model_version = MODEL_VERSION_TRAINED
            except Exception:
                logger.exception("trained model inference failed; using rules fallback")
                p_on_time = _rules_based_p_on_time(features)
                model_version = MODEL_VERSION_FALLBACK
        else:
            p_on_time = _rules_based_p_on_time(features)
            model_version = MODEL_VERSION_FALLBACK

        expected_delay = features.avg_delay_days if features.avg_delay_days > 0 else None
        return SupplierPrediction(
            supplier_id=features.supplier_id,
            p_on_time=p_on_time,
            expected_delay_days_if_late=expected_delay,
            p_price_holds=None,
            confidence_band=_confidence_band(features.n_observations),  # type: ignore[arg-type]
            based_on_n_observations=features.n_observations,
            top_features=_top_features_from_features(features),
            model_version=model_version,
        )

    @staticmethod
    def feature_names() -> list[str]:
        return list(FEATURE_NAMES)
