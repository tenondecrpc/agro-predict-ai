"""Pydantic schemas for LLM agent inputs and outputs.

These are intentionally separate from the domain models in
``backend.procurement.models``: the extractor produces a *preview*
(``ExtractedQuotation``) that the buyer confirms before it becomes a
domain ``Quotation``.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


class ExtractedItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    brand: str | None = None
    model: str | None = None
    origin: str | None = None
    presentation: str | None = None
    lead_time_days: int | None = None


class ExtractedQuotation(BaseModel):
    """LLM extraction preview. The user confirms before persisting."""

    model_config = ConfigDict(extra="ignore")

    supplier_legal_name: str | None = None
    supplier_ruc: str | None = None
    currency: Literal["PYG", "USD", "EUR", "BRL", "ARS"] = "PYG"
    exchange_rate_quoted: Decimal | None = None
    incoterm: str | None = None
    includes_iva: bool = True
    iva_rate: Decimal | None = None
    payment_terms: str | None = None
    total_amount: Decimal
    lead_time_days: int = Field(..., ge=0, le=365)
    validity_until_iso: date
    warranty_months: int | None = None
    discount_pct: Decimal | None = None
    items: list[ExtractedItem] = Field(default_factory=list)
    extraction_confidence: Decimal = Field(default=Decimal("0.5"), ge=Decimal("0"), le=Decimal("1"))
    extraction_source: Literal["llm", "fallback"] = "llm"


# ---------------------------------------------------------------------------
# Comparator
# ---------------------------------------------------------------------------


class NormalizedItemBySupplier(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_id: str
    matched_description: str
    unit_price_pyg: Decimal
    quantity: Decimal
    subtotal_pyg: Decimal


class NormalizedItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    request_item_description: str
    by_supplier: list[NormalizedItemBySupplier] = Field(default_factory=list)


class SupplierTotals(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_id: str
    supplier_legal_name: str
    total_pyg: Decimal
    lead_time_days: int
    warranty_months: int | None = None
    payment_terms: str | None = None


class BestInCriterion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    price: str | None = None
    delivery: str | None = None
    warranty: str | None = None
    terms: str | None = None


class SignificantDifference(BaseModel):
    model_config = ConfigDict(extra="ignore")

    criterion: str
    description: str
    supplier_ids_involved: list[str] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    items_normalized: list[NormalizedItem] = Field(default_factory=list)
    totals_by_supplier: list[SupplierTotals] = Field(default_factory=list)
    best_in_criterion: BestInCriterion = Field(default_factory=BestInCriterion)
    significant_differences: list[SignificantDifference] = Field(default_factory=list)
    source: Literal["llm", "fallback"] = "llm"


# ---------------------------------------------------------------------------
# Recommender
# ---------------------------------------------------------------------------


class Recommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommended_quotation_id: str
    recommended_supplier_id: str
    decision_band: Literal[
        "buy_now",
        "negotiate_and_close",
        "buy_with_followup",
        "wait_better_offer",
        "not_recommended",
    ]
    composite_score: Decimal
    urgency_score: Decimal
    offer_score: Decimal
    reasoning_markdown: str
    source: Literal["llm", "fallback"] = "llm"


# ---------------------------------------------------------------------------
# Negotiator
# ---------------------------------------------------------------------------


class NegotiationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_text: str
    tone: Literal["cordial", "formal", "asertivo"] = "cordial"
    target_improvements: dict = Field(default_factory=dict)
    source: Literal["llm", "fallback"] = "llm"
