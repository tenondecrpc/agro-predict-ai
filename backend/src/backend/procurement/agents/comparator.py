"""LLM Agent #2: comparator that normalizes N quotations side by side.

Input: a ``PurchaseRequest`` plus all its validated quotations.
Output: a ``ComparisonResult`` with normalized totals, item matching,
best-in-criterion winners, and significant differences flagged.

Fallback: a deterministic comparator that emits totals and best-in
without semantic item matching.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from decimal import Decimal

from pydantic import ValidationError

from backend.llm.adapter import LLMAdapter
from backend.procurement.agents.base import (
    extract_json,
    is_llm_available,
    safe_complete,
    validate_to_model,
)
from backend.procurement.agents.prompts import COMPARATOR_PROMPT_TEMPLATE, COMPARATOR_SYSTEM
from backend.procurement.agents.schemas import (
    BestInCriterion,
    ComparisonResult,
    SignificantDifference,
    SupplierTotals,
)
from backend.procurement.models import PurchaseRequest, Quotation, Supplier

logger = logging.getLogger(__name__)


def _summarize_request(request: PurchaseRequest) -> str:
    return json.dumps(
        {
            "request_id": request.request_id,
            "title": request.title,
            "target_crop": request.target_crop,
            "target_zafra": request.target_zafra,
            "fenological_window": request.fenological_window,
            "delivery_department": request.delivery_department,
            "criteria_weights": request.criteria_weights.model_dump(),
            "items": [
                {"item_id": i.item_id, "description": i.description, "quantity": str(i.quantity), "unit": i.unit}
                for i in request.items
            ],
        },
        default=str,
    )


def _summarize_quotations(quotations: list[Quotation], suppliers_by_id: dict[str, Supplier]) -> str:
    serializable = []
    for q in quotations:
        sup = suppliers_by_id.get(q.supplier_id)
        serializable.append(
            {
                "quotation_id": q.quotation_id,
                "supplier_id": q.supplier_id,
                "supplier_legal_name": sup.legal_name if sup else None,
                "currency": q.currency,
                "exchange_rate_quoted": str(q.exchange_rate_quoted) if q.exchange_rate_quoted else None,
                "includes_iva": q.includes_iva,
                "total_amount": str(q.total_amount),
                "total_pyg_normalized": str(q.total_pyg_normalized) if q.total_pyg_normalized else None,
                "lead_time_days": q.lead_time_days,
                "warranty_months": q.warranty_months,
                "payment_terms": q.payment_terms,
                "items": [
                    {
                        "description": i.description,
                        "quantity": str(i.quantity),
                        "unit_price": str(i.unit_price),
                        "subtotal": str(i.subtotal),
                        "presentation": i.presentation,
                        "origin": i.origin,
                    }
                    for i in q.items
                ],
            }
        )
    return json.dumps(serializable, default=str)


def _normalize_total_pyg(q: Quotation, fx_rate_usd_pyg: Decimal | None) -> Decimal:
    """Pick the best available PYG total for fallback comparisons."""
    if q.total_pyg_normalized is not None:
        return q.total_pyg_normalized
    if q.currency == "PYG":
        return q.total_amount
    if q.currency == "USD" and fx_rate_usd_pyg is not None:
        return (q.total_amount * fx_rate_usd_pyg).quantize(Decimal("0.01"))
    # Other currencies fall back to face value (visible in the comparison
    # so the user notices the missing FX).
    return q.total_amount


def fallback_compare(
    request: PurchaseRequest,
    quotations: Iterable[Quotation],
    suppliers_by_id: dict[str, Supplier],
    *,
    fx_rate_usd_pyg: Decimal | None = None,
) -> ComparisonResult:
    quotes = list(quotations)
    if not quotes:
        return ComparisonResult(source="fallback")

    totals = []
    for q in quotes:
        sup = suppliers_by_id.get(q.supplier_id)
        totals.append(
            SupplierTotals(
                supplier_id=q.supplier_id,
                supplier_legal_name=sup.legal_name if sup else q.supplier_id,
                total_pyg=_normalize_total_pyg(q, fx_rate_usd_pyg),
                lead_time_days=q.lead_time_days,
                warranty_months=q.warranty_months,
                payment_terms=q.payment_terms,
            )
        )

    cheapest = min(totals, key=lambda t: t.total_pyg)
    fastest = min(totals, key=lambda t: t.lead_time_days)
    best_warranty: SupplierTotals | None = None
    if any(t.warranty_months for t in totals):
        best_warranty = max(totals, key=lambda t: t.warranty_months or 0)

    differences: list[SignificantDifference] = []
    if len(totals) >= 2:
        sorted_totals = sorted(totals, key=lambda t: t.total_pyg)
        gap = (sorted_totals[-1].total_pyg - sorted_totals[0].total_pyg) / sorted_totals[0].total_pyg
        if gap > Decimal("0.10"):
            differences.append(
                SignificantDifference(
                    criterion="price",
                    description=f"price gap {gap:.0%} between cheapest and most expensive supplier",
                    supplier_ids_involved=[sorted_totals[0].supplier_id, sorted_totals[-1].supplier_id],
                )
            )
        sorted_lt = sorted(totals, key=lambda t: t.lead_time_days)
        if sorted_lt[-1].lead_time_days - sorted_lt[0].lead_time_days >= 7:
            differences.append(
                SignificantDifference(
                    criterion="delivery",
                    description=(
                        f"lead time gap {sorted_lt[-1].lead_time_days - sorted_lt[0].lead_time_days} days"
                    ),
                    supplier_ids_involved=[sorted_lt[0].supplier_id, sorted_lt[-1].supplier_id],
                )
            )

    return ComparisonResult(
        items_normalized=[],
        totals_by_supplier=totals,
        best_in_criterion=BestInCriterion(
            price=cheapest.supplier_id,
            delivery=fastest.supplier_id,
            warranty=best_warranty.supplier_id if best_warranty else None,
        ),
        significant_differences=differences,
        source="fallback",
    )


class ComparatorAgent:
    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    def compare(
        self,
        request: PurchaseRequest,
        quotations: list[Quotation],
        suppliers_by_id: dict[str, Supplier],
        *,
        fx_rate_usd_pyg: Decimal | None = None,
    ) -> ComparisonResult:
        if not quotations:
            return ComparisonResult(source="fallback")

        if not is_llm_available(self._llm):
            return fallback_compare(request, quotations, suppliers_by_id, fx_rate_usd_pyg=fx_rate_usd_pyg)

        prompt = COMPARATOR_PROMPT_TEMPLATE.format(
            request_summary=_summarize_request(request),
            quotations_json=_summarize_quotations(quotations, suppliers_by_id),
        )
        response = safe_complete(self._llm, system=COMPARATOR_SYSTEM, prompt=prompt)
        if response is None:
            return fallback_compare(request, quotations, suppliers_by_id, fx_rate_usd_pyg=fx_rate_usd_pyg)

        try:
            data = extract_json(response)
            return validate_to_model(data, ComparisonResult)
        except (ValueError, ValidationError) as exc:
            logger.warning("comparator LLM output unusable: %s", exc)
            return fallback_compare(request, quotations, suppliers_by_id, fx_rate_usd_pyg=fx_rate_usd_pyg)
