"""Training script for AgroPredict AI corn yield prediction model.

Generates a synthetic dataset, trains a RandomForestRegressor, validates accuracy,
and saves the model artifact and metadata.

Usage:
    uv run --project backend python backend/scripts/train_model.py
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).parent.parent / "models"
N_SAMPLES = 2000
RANDOM_STATE = 42
MIN_R2 = 0.60
FEATURE_NAMES = ["soil_moisture", "temperature_c", "rainfall_mm"]


def generate_dataset(n_samples: int = N_SAMPLES, random_state: int = RANDOM_STATE) -> tuple[np.ndarray, np.ndarray]:
    """Generate synthetic crop yield dataset."""
    rng = np.random.default_rng(random_state)
    soil_moisture = rng.uniform(0.1, 0.9, n_samples)
    temperature_c = rng.uniform(10.0, 35.0, n_samples)
    rainfall_mm = rng.uniform(10.0, 100.0, n_samples)

    noise = rng.normal(0, 0.3, n_samples)
    yield_target = 3.0 + soil_moisture * 8.0 + temperature_c * 0.12 + rainfall_mm * 0.025 + noise

    X = np.column_stack([soil_moisture, temperature_c, rainfall_mm])
    y = yield_target
    return X, y


def compute_dataset_hash(X: np.ndarray, y: np.ndarray) -> str:
    """Compute a deterministic hash of the dataset."""
    data_bytes = X.tobytes() + y.tobytes()
    return hashlib.sha256(data_bytes).hexdigest()


def train_model(X_train: np.ndarray, y_train: np.ndarray) -> RandomForestRegressor:
    """Train a RandomForestRegressor on the provided data."""
    model = RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE, n_jobs=-1)
    model.fit(X_train, y_train)
    return model


def compute_quantiles(X: np.ndarray) -> dict[str, dict[str, float]]:
    """Compute p1 and p99 quantiles per feature for OOD detection."""
    quantiles: dict[str, dict[str, float]] = {}
    for i, name in enumerate(FEATURE_NAMES):
        quantiles[name] = {
            "p1": float(np.percentile(X[:, i], 1)),
            "p99": float(np.percentile(X[:, i], 99)),
        }
    return quantiles


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Generating synthetic dataset with %d samples ...", N_SAMPLES)
    X, y = generate_dataset()
    dataset_hash = compute_dataset_hash(X, y)
    logger.info("Dataset hash: %s", dataset_hash)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=RANDOM_STATE)
    logger.info("Training set: %d samples, test set: %d samples", len(X_train), len(X_test))

    logger.info("Training RandomForestRegressor ...")
    model = train_model(X_train, y_train)

    y_pred = model.predict(X_test)
    r2 = float(r2_score(y_test, y_pred))
    mae = float(mean_absolute_error(y_test, y_pred))
    rmse = float(mean_squared_error(y_test, y_pred) ** 0.5)

    logger.info("Test R2: %.4f | MAE: %.4f | RMSE: %.4f", r2, mae, rmse)

    if r2 < MIN_R2:
        logger.error("R2 score %.4f is below minimum threshold %.2f. Aborting.", r2, MIN_R2)
        sys.exit(1)

    hash_short = dataset_hash[:8]
    artifact_name = f"corn_rf_v1.0.0_{hash_short}.joblib"
    artifact_path = MODELS_DIR / artifact_name
    metadata_path = MODELS_DIR / "corn_rf_v1.0.0_metadata.json"

    logger.info("Saving model artifact to %s ...", artifact_path)
    joblib.dump(model, artifact_path)

    feature_quantiles = compute_quantiles(X)
    metadata = {
        "version": "v1.0.0",
        "trained_at": datetime.now(UTC).isoformat(),
        "dataset_hash": dataset_hash,
        "mae": round(mae, 6),
        "rmse": round(rmse, 6),
        "r2": round(r2, 6),
        "feature_names": FEATURE_NAMES,
        "artifact_path": str(artifact_path),
        "artifact_name": artifact_name,
        "p1_quantiles": {name: quantiles["p1"] for name, quantiles in feature_quantiles.items()},
        "p99_quantiles": {name: quantiles["p99"] for name, quantiles in feature_quantiles.items()},
    }

    logger.info("Saving metadata to %s ...", metadata_path)
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Training complete. R2=%.4f, MAE=%.4f, RMSE=%.4f", r2, mae, rmse)
    logger.info("Artifact: %s", artifact_path)
    logger.info("Metadata: %s", metadata_path)

    # Print env var hint for ML_MODEL_PATH
    rel_path = os.path.relpath(str(artifact_path), start=str(Path(__file__).parent.parent.parent))
    logger.info("Set ML_MODEL_PATH=%s to use this model", rel_path)


if __name__ == "__main__":
    main()
