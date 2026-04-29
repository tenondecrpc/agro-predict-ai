"""Feature engineering for the supplier performance predictor."""

from __future__ import annotations

import statistics
from datetime import date

from backend.procurement.ml.models import SupplierFeatures, SupplierPerformanceRecord


def extract_features(
    supplier_id: str,
    history: list[SupplierPerformanceRecord],
    *,
    today: date | None = None,
) -> SupplierFeatures:
    """Aggregate a supplier's history into a fixed feature vector.

    History is sorted by awarded_date descending so the "last_3" /
    "last_6" buckets reflect the most recent deliveries.
    """

    today = today or date.today()
    records = sorted(
        [h for h in history if h.supplier_id == supplier_id],
        key=lambda h: h.awarded_date,
        reverse=True,
    )
    n = len(records)
    if n == 0:
        return SupplierFeatures(supplier_id=supplier_id, n_observations=0)

    decided = [r for r in records if r.delivered_on_time is not None]

    def on_time_rate(window: list[SupplierPerformanceRecord]) -> float:
        if not window:
            return 0.0
        flags = [1.0 if r.delivered_on_time else 0.0 for r in window if r.delivered_on_time is not None]
        return sum(flags) / len(flags) if flags else 0.0

    last_3 = decided[:3]
    last_6 = decided[:6]
    delays = [r.days_delay for r in decided if r.days_delay is not None and not r.delivered_on_time]
    delays = [d for d in delays if d is not None and d > 0]
    avg_delay = statistics.fmean(delays) if delays else 0.0
    p90_delay = (
        statistics.quantiles(delays, n=10)[-1] if len(delays) >= 5 else (max(delays) if delays else 0.0)
    )

    categories = [r.category for r in records if r.category]
    category_consistency = 0.0
    if categories:
        most_common = max(set(categories), key=categories.count)
        category_consistency = categories.count(most_common) / len(categories)

    earliest = min(r.awarded_date for r in records)
    months_active = max(1, (today.year - earliest.year) * 12 + (today.month - earliest.month))
    last_delivery = records[0].awarded_date
    last_delivery_days_ago = (today - last_delivery).days

    return SupplierFeatures(
        supplier_id=supplier_id,
        n_observations=n,
        on_time_rate_all=on_time_rate(decided),
        on_time_rate_last_3=on_time_rate(last_3),
        on_time_rate_last_6=on_time_rate(last_6),
        avg_delay_days=float(avg_delay),
        p90_delay_days=float(p90_delay),
        category_consistency=category_consistency,
        months_active=months_active,
        last_delivery_days_ago=last_delivery_days_ago,
    )


def to_vector(features: SupplierFeatures) -> list[float]:
    """Order the feature vector for model input. Order is part of the contract."""
    return [
        features.on_time_rate_all,
        features.on_time_rate_last_3,
        features.on_time_rate_last_6,
        features.avg_delay_days,
        features.p90_delay_days,
        features.category_consistency,
        float(features.months_active),
        float(features.last_delivery_days_ago or 999),
        float(features.n_observations),
    ]


FEATURE_NAMES: list[str] = [
    "on_time_rate_all",
    "on_time_rate_last_3",
    "on_time_rate_last_6",
    "avg_delay_days",
    "p90_delay_days",
    "category_consistency",
    "months_active",
    "last_delivery_days_ago",
    "n_observations",
]
