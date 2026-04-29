"""Schemas for the ML layer (supplier performance + predictions + anomaly)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

ConfidenceBand = Literal["low", "medium", "high"]


class SupplierPerformanceRecord(BaseModel):
    """One historical delivery used to train and to compute features."""

    model_config = ConfigDict(extra="forbid")

    history_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    supplier_id: str
    quotation_id: str | None = None
    category: str | None = None
    awarded_date: date
    promised_delivery_date: date
    actual_delivery_date: date | None = None
    delivered_on_time: bool | None = None
    days_delay: int | None = None
    price_at_award: Decimal | None = None
    price_actual: Decimal | None = None
    quality_score: Decimal | None = None
    notes: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SupplierFeatures(BaseModel):
    """Aggregated features extracted from a supplier's history."""

    model_config = ConfigDict(extra="forbid")

    supplier_id: str
    n_observations: int
    on_time_rate_all: float = 0.0
    on_time_rate_last_3: float = 0.0
    on_time_rate_last_6: float = 0.0
    avg_delay_days: float = 0.0
    p90_delay_days: float = 0.0
    category_consistency: float = 0.0
    months_active: int = 0
    last_delivery_days_ago: int | None = None


class SupplierPrediction(BaseModel):
    """Cached output of the supplier performance predictor."""

    model_config = ConfigDict(extra="forbid")

    supplier_id: str
    p_on_time: float = Field(..., ge=0.0, le=1.0)
    expected_delay_days_if_late: float | None = None
    p_price_holds: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence_band: ConfidenceBand
    based_on_n_observations: int
    top_features: list[str] = Field(default_factory=list)
    model_version: str
    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AnomalyResult(BaseModel):
    """Output of the price anomaly detector for a quotation."""

    model_config = ConfigDict(extra="forbid")

    quotation_id: str
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    z_score_max: float
    flagged: bool
    reason: str | None = None
    category_checked: str | None = None
    expected_min_usd: Decimal | None = None
    expected_max_usd: Decimal | None = None
    observed_unit_price_usd: Decimal | None = None
