"""Pydantic schemas for external signals (weather + FX)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

RiskBand = Literal["low", "moderate", "moderate-high", "high", "extreme"]


class WeatherComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    precipitation_sum_mm: Decimal | None = None
    heat_stress_days: int | None = None
    excess_rain_days: int | None = None
    max_temp_c: Decimal | None = None
    min_temp_c: Decimal | None = None


class WeatherSnapshot(BaseModel):
    """A cached weather forecast for a Paraguayan department."""

    model_config = ConfigDict(extra="forbid")

    snapshot_id: str = Field(default_factory=lambda: str(uuid4()))
    department: str
    geo_lat: Decimal
    geo_lng: Decimal
    horizon_days: int = Field(..., ge=1, le=16)
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime
    components: WeatherComponents = Field(default_factory=WeatherComponents)
    weather_risk_score: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    risk_band: RiskBand
    interpretation: str | None = None
    raw_response: dict = Field(default_factory=dict)
    source: str = "open-meteo"


class FXRate(BaseModel):
    """A cached USD-to-PYG (or any pair) exchange rate."""

    model_config = ConfigDict(extra="forbid")

    rate_id: str = Field(default_factory=lambda: str(uuid4()))
    base_currency: str = "USD"
    quote_currency: str = "PYG"
    rate_buy: Decimal | None = None
    rate_sell: Decimal | None = None
    rate_reference: Decimal
    source: str
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    valid_until: datetime
    raw_response: dict = Field(default_factory=dict)
