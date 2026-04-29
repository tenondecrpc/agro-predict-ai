"""Train the supplier performance predictor.

Generates ~500 synthetic deliveries calibrated to LATAM agro
procurement benchmarks (3 top quartile suppliers at >=90 percent
on-time, 5 mid quartile at 70-85 percent, 4 bottom quartile at
45-65 percent), trains a gradient boosting classifier, and
persists the model artifact next to the existing crop model.

Run as:

    uv run --project backend python -m backend.procurement.ml.train
"""

from __future__ import annotations

import logging
import random
from datetime import date, timedelta
from pathlib import Path

import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

from backend.procurement.ml.features import (
    SupplierPerformanceRecord,
    extract_features,
    to_vector,
)
from backend.procurement.ml.supplier_predictor import DEFAULT_MODEL_PATH

logger = logging.getLogger(__name__)

CATEGORIES = ["fertilizante", "semilla", "fitosanitario", "maquinaria"]


def _synthetic_history(seed: int = 42) -> list[SupplierPerformanceRecord]:
    rng = random.Random(seed)
    today = date.today()

    profiles = (
        # supplier_id, on_time_rate, mean_delay, n_records
        [(f"top-{i}", 0.92 + rng.uniform(-0.02, 0.04), 1.5, 30) for i in range(3)]
        + [(f"mid-{i}", 0.78 + rng.uniform(-0.05, 0.05), 4.0, 35) for i in range(5)]
        + [(f"bot-{i}", 0.55 + rng.uniform(-0.10, 0.05), 8.0, 25) for i in range(4)]
    )

    records: list[SupplierPerformanceRecord] = []
    for supplier_id, on_time_rate, mean_delay, n in profiles:
        category = rng.choice(CATEGORIES)
        for _ in range(n):
            awarded = today - timedelta(days=rng.randint(7, 720))
            promised = awarded + timedelta(days=rng.randint(5, 25))
            on_time = rng.random() < on_time_rate
            delay_days = 0 if on_time else max(1, int(rng.gauss(mean_delay, 2.0)))
            actual = promised + timedelta(days=delay_days)
            cat = category if rng.random() < 0.85 else rng.choice(CATEGORIES)
            records.append(
                SupplierPerformanceRecord(
                    tenant_id="tenant-train",
                    supplier_id=supplier_id,
                    category=cat,
                    awarded_date=awarded,
                    promised_delivery_date=promised,
                    actual_delivery_date=actual,
                    delivered_on_time=on_time,
                    days_delay=delay_days,
                )
            )
    return records


def _build_dataset(records: list[SupplierPerformanceRecord]) -> tuple[list[list[float]], list[int]]:
    """Per-record sample: features computed from history strictly before
    the record's awarded_date, label is whether the record was on_time.
    """

    by_supplier: dict[str, list[SupplierPerformanceRecord]] = {}
    for r in records:
        by_supplier.setdefault(r.supplier_id, []).append(r)

    rows: list[list[float]] = []
    labels: list[int] = []
    for supplier_id, hist in by_supplier.items():
        hist_sorted = sorted(hist, key=lambda r: r.awarded_date)
        for i, target in enumerate(hist_sorted):
            if i < 3 or target.delivered_on_time is None:
                continue  # need at least 3 prior observations
            past = hist_sorted[:i]
            features = extract_features(supplier_id, past, today=target.awarded_date)
            if features.n_observations == 0:
                continue
            rows.append(to_vector(features))
            labels.append(1 if target.delivered_on_time else 0)
    return rows, labels


def train(
    *,
    output_path: Path | None = None,
    random_state: int = 42,
) -> dict[str, object]:
    output_path = output_path or DEFAULT_MODEL_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = _synthetic_history(seed=random_state)
    X, y = _build_dataset(records)
    if not X:
        raise RuntimeError("synthetic dataset produced no training rows")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state, stratify=y
    )
    model = GradientBoostingClassifier(
        n_estimators=120,
        max_depth=3,
        learning_rate=0.08,
        random_state=random_state,
    )
    model.fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, proba) if len(set(y_test)) > 1 else float("nan")

    joblib.dump(model, output_path)

    return {
        "output_path": str(output_path),
        "rows_total": len(X),
        "rows_train": len(X_train),
        "rows_test": len(X_test),
        "positive_rate_train": sum(y_train) / len(y_train),
        "auc": auc,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    metrics = train()
    print("Procurement supplier predictor trained:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":  # pragma: no cover
    main()
