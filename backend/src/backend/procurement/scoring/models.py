"""Schemas for the dual scoring layer (Urgency + Offer)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

DecisionBand = Literal[
    "buy_now",
    "negotiate_and_close",
    "buy_with_followup",
    "wait_better_offer",
    "not_recommended",
]

VolatilityLevel = Literal["low", "medium", "high"]


class UrgencyComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weather_risk: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    delivery_urgency: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    market_volatility: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))


class OfferComponents(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supplier_score: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    commercial_terms_score: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    delivery_risk: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))


class ProcurementScore(BaseModel):
    """Dual score per (request, quotation) plus the decision band."""

    model_config = ConfigDict(extra="forbid")

    score_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    request_id: str
    quotation_id: str
    urgency: UrgencyComponents
    urgency_score: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    offer: OfferComponents
    offer_score: Decimal = Field(..., ge=Decimal("0"), le=Decimal("100"))
    decision_band: DecisionBand
    components_json: dict = Field(default_factory=dict)
    computed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
