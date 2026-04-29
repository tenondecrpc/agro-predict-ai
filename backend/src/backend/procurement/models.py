"""Pydantic schemas for the procurement domain (spec 018).

These models mirror the procurement database tables. They are used both
as the API surface (request and response bodies) and as the canonical
internal representation that flows between the repository, service, and
agents.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class PurchaseRequestStatus(StrEnum):
    DRAFT = "draft"
    IN_QUOTING = "in_quoting"
    READY_FOR_REVIEW = "ready_for_review"
    RECOMMENDED = "recommended"
    APPROVED = "approved"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class QuotationStatus(StrEnum):
    UPLOADED = "uploaded"
    VALIDATED = "validated"
    QUARANTINED = "quarantined"
    AWARDED = "awarded"
    REJECTED = "rejected"


class SupplierStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Urgency(StrEnum):
    NORMAL = "normal"
    URGENTE = "urgente"
    CRITICA = "critica"


# ---------------------------------------------------------------------------
# Suppliers
# ---------------------------------------------------------------------------


class SupplierCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    legal_name: str = Field(..., min_length=1, max_length=300)
    ruc: str | None = Field(default=None, max_length=32)
    commercial_name: str | None = Field(default=None, max_length=300)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=64)
    country: str = Field(default="PY", max_length=64)
    primary_categories: str | None = Field(default=None, max_length=500)
    primary_origin_countries: str | None = Field(default=None, max_length=200)
    is_importer: bool = False
    senave_registered: bool = False
    iso_certified: bool = False
    risk_tier: str = Field(default="unknown", max_length=32)


class Supplier(SupplierCreate):
    supplier_id: str = Field(default_factory=lambda: str(uuid4()))
    status: SupplierStatus = SupplierStatus.ACTIVE
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Purchase requests
# ---------------------------------------------------------------------------


class CriteriaWeights(BaseModel):
    """Multi-criteria weights for the recommendation. Must sum to 100."""

    model_config = ConfigDict(extra="forbid")

    price: int = 40
    delivery: int = 30
    quality: int = 20
    terms: int = 10

    @field_validator("price", "delivery", "quality", "terms")
    @classmethod
    def _non_negative(cls, value: int) -> int:
        if value < 0 or value > 100:
            raise ValueError("each weight must be in [0, 100]")
        return value

    def validate_sum(self) -> None:
        total = self.price + self.delivery + self.quality + self.terms
        if total != 100:
            raise ValueError(f"criteria weights must sum to 100 (got {total})")


class RequestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(default_factory=lambda: str(uuid4()))
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit: str = Field(default="unit", max_length=32)
    specifications: str | None = None
    target_unit_price: Decimal | None = None
    position: int = 0


class PurchaseRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    team_id: str
    requested_by: str
    title: str = Field(..., min_length=1, max_length=300)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)
    urgency: Urgency = Urgency.NORMAL
    currency: str = Field(default="PYG", max_length=8)
    budget_cap: Decimal | None = None
    criteria_weights: CriteriaWeights = Field(default_factory=CriteriaWeights)
    target_delivery_date: date
    # Agro vertical fields
    target_crop: str | None = Field(default=None, max_length=64)
    target_zafra: str | None = Field(default=None, max_length=64)
    fenological_window: str | None = Field(default=None, max_length=64)
    target_hectares: Decimal | None = None
    delivery_department: str | None = Field(default=None, max_length=64)
    delivery_location: str | None = Field(default=None, max_length=300)
    current_stock_days: int | None = None
    items: list[RequestItem] = Field(default_factory=list)


class PurchaseRequest(PurchaseRequestCreate):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    status: PurchaseRequestStatus = PurchaseRequestStatus.DRAFT
    approver_id: str | None = None
    approved_at: datetime | None = None
    awarded_quotation_id: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Quotations
# ---------------------------------------------------------------------------


class QuotationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(default_factory=lambda: str(uuid4()))
    request_item_id: str | None = None
    description: str = Field(..., min_length=1, max_length=500)
    quantity: Decimal = Field(..., gt=Decimal("0"))
    unit_price: Decimal = Field(..., ge=Decimal("0"))
    subtotal: Decimal = Field(..., ge=Decimal("0"))
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    origin: str | None = Field(default=None, max_length=120)
    presentation: str | None = Field(default=None, max_length=120)
    lead_time_days: int | None = None
    notes: str | None = Field(default=None, max_length=500)


class QualityFlag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "validity_expired",
        "currency_not_supported",
        "lead_time_implausible",
        "unit_mismatch",
        "missing_total",
        "negative_amount",
        "supplier_not_found",
        "request_not_found",
    ]
    message: str
    field: str | None = None


class QuotationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    request_id: str
    supplier_id: str
    created_by: str
    currency: str = Field(default="PYG", max_length=8)
    exchange_rate_quoted: Decimal | None = None
    incoterm: str | None = Field(default=None, max_length=32)
    includes_iva: bool = True
    iva_rate: Decimal | None = None
    payment_terms: str | None = Field(default=None, max_length=200)
    total_amount: Decimal = Field(..., ge=Decimal("0"))
    total_pyg_normalized: Decimal | None = None
    lead_time_days: int = Field(..., ge=0, le=365)
    validity_until: date
    warranty_months: int | None = None
    discount_pct: Decimal | None = None
    terms_text: str | None = None
    attachment_ref: str | None = Field(default=None, max_length=500)
    raw_extracted_text: str | None = None
    extraction_confidence: Decimal | None = None
    items: list[QuotationItem] = Field(default_factory=list)


class Quotation(QuotationCreate):
    quotation_id: str = Field(default_factory=lambda: str(uuid4()))
    anomaly_score: Decimal | None = None
    anomaly_reason: str | None = None
    status: QuotationStatus = QuotationStatus.UPLOADED
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class ProcurementAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    team_id: str | None = None
    actor: str
    action: str = Field(..., min_length=1, max_length=100)
    entity_type: Literal[
        "purchase_request",
        "supplier",
        "quotation",
    ]
    entity_id: str
    payload_summary: dict = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Agro catalog
# ---------------------------------------------------------------------------


class AgroCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku_code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=300)
    category: Literal[
        "fertilizante",
        "semilla",
        "fitosanitario",
        "maquinaria",
        "repuesto",
        "combustible",
        "otro",
    ]
    subcategory: str | None = Field(default=None, max_length=120)
    standard_unit: str = Field(default="unit", max_length=32)
    typical_presentation: str | None = Field(default=None, max_length=120)
    iva_rate: Decimal = Decimal("10.00")
    market_price_min_usd: Decimal | None = None
    market_price_max_usd: Decimal | None = None
    market_price_currency: str = "USD"
    last_market_price_update: date | None = None
    senave_required: bool = False
    notes: str | None = Field(default=None, max_length=500)
