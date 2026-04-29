"""Data quality gate for quotations (spec 018, FR-006).

Runs deterministic structural checks before any AI agent reads a
quotation. Returns the list of flags found; callers decide whether to
quarantine based on the policy "any flag with severity >= block leads
to status=quarantined".
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from decimal import Decimal

from backend.procurement.models import (
    PurchaseRequest,
    QualityFlag,
    Quotation,
    Supplier,
)

# Currencies the platform supports out of the box. Tenant-level allowlists
# can be layered on top in a follow-up; for the MVP this set is enough to
# cover Paraguay agro procurement (PYG, USD) and to demonstrate rejection
# of unsupported currencies.
SUPPORTED_CURRENCIES: frozenset[str] = frozenset({"PYG", "USD", "EUR", "BRL", "ARS"})

LEAD_TIME_MIN_DAYS = 0
LEAD_TIME_MAX_DAYS = 365


def evaluate_quotation(
    quotation: Quotation,
    *,
    request: PurchaseRequest | None,
    supplier: Supplier | None,
    today: date | None = None,
) -> list[QualityFlag]:
    """Return a list of quality flags found on the quotation.

    An empty list means the quotation is structurally valid and can
    transition to status=validated. Any non-empty list quarantines it.
    """

    flags: list[QualityFlag] = []
    today = today or date.today()

    if request is None:
        flags.append(
            QualityFlag(
                code="request_not_found",
                message="Referenced purchase request does not exist for this tenant.",
                field="request_id",
            )
        )

    if supplier is None:
        flags.append(
            QualityFlag(
                code="supplier_not_found",
                message="Referenced supplier does not exist for this tenant.",
                field="supplier_id",
            )
        )

    if quotation.currency not in SUPPORTED_CURRENCIES:
        flags.append(
            QualityFlag(
                code="currency_not_supported",
                message=(
                    f"Currency '{quotation.currency}' is not supported. "
                    f"Allowed: {sorted(SUPPORTED_CURRENCIES)}."
                ),
                field="currency",
            )
        )

    if quotation.validity_until < today:
        flags.append(
            QualityFlag(
                code="validity_expired",
                message=(
                    f"Quotation validity expired on {quotation.validity_until.isoformat()} "
                    f"(today: {today.isoformat()})."
                ),
                field="validity_until",
            )
        )

    if quotation.lead_time_days < LEAD_TIME_MIN_DAYS or quotation.lead_time_days > LEAD_TIME_MAX_DAYS:
        flags.append(
            QualityFlag(
                code="lead_time_implausible",
                message=(
                    f"Lead time {quotation.lead_time_days} is outside the plausible "
                    f"range [{LEAD_TIME_MIN_DAYS}, {LEAD_TIME_MAX_DAYS}] days."
                ),
                field="lead_time_days",
            )
        )

    if quotation.total_amount <= Decimal("0"):
        flags.append(
            QualityFlag(
                code="missing_total",
                message="Total amount must be greater than zero.",
                field="total_amount",
            )
        )

    if any(item.unit_price < Decimal("0") or item.subtotal < Decimal("0") for item in quotation.items):
        flags.append(
            QualityFlag(
                code="negative_amount",
                message="Quotation contains items with negative unit_price or subtotal.",
                field="items",
            )
        )

    if request is not None and quotation.items and request.items:
        unit_mismatch = _detect_unit_mismatch(quotation, request)
        if unit_mismatch:
            flags.append(unit_mismatch)

    return flags


def _detect_unit_mismatch(quotation: Quotation, request: PurchaseRequest) -> QualityFlag | None:
    """Soft check: if a quotation item references a request item, both
    should agree on the unit of measure. Cross-quote unit consistency
    (FR spec acceptance scenario 3.2) is a Phase 2 enhancement.
    """

    request_units_by_item = {item.item_id: item.unit for item in request.items}
    for q_item in quotation.items:
        if q_item.request_item_id is None:
            continue
        expected_unit = request_units_by_item.get(q_item.request_item_id)
        if expected_unit is None:
            continue
        # presentation may carry the unit context (for example "bolsa 50kg" against "kg")
        if expected_unit.lower() not in (q_item.presentation or "").lower() and expected_unit.lower() not in (
            q_item.notes or ""
        ).lower():
            # Heuristic: only flag when the request unit is also not implied by description
            if expected_unit.lower() not in q_item.description.lower():
                return QualityFlag(
                    code="unit_mismatch",
                    message=(
                        f"Quotation item references request item {q_item.request_item_id} "
                        f"but unit '{expected_unit}' is not present in the item's description, "
                        "presentation, or notes."
                    ),
                    field="items",
                )
    return None


def is_blocking(flags: Iterable[QualityFlag]) -> bool:
    """Every flag in this gate is blocking. Reserved for future severity tiers."""
    return any(True for _ in flags)
