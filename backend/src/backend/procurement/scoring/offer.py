"""Offer Score: 'which supplier offer is most attractive?'

Formula (per ``compras/COMPRAS_AGRO_plan.md``):

    offer = 0.35 * supplier_score
          + 0.40 * commercial_terms_score
          + 0.25 * (100 - delivery_risk)

All inputs are 0-100. ``supplier_score`` comes from the ML predictor
(probability of on-time delivery scaled to 0-100). ``commercial_terms``
combines price competitiveness, payment terms, warranty, and the like.
``delivery_risk`` aggregates ML expected delay, anomaly score, and
import-supply-chain factors.
"""

from __future__ import annotations

from decimal import Decimal

from backend.procurement.ml.models import AnomalyResult, SupplierPrediction
from backend.procurement.scoring.models import OfferComponents

WEIGHT_SUPPLIER = Decimal("0.35")
WEIGHT_TERMS = Decimal("0.40")
WEIGHT_DELIVERY_INV = Decimal("0.25")  # applied to (100 - delivery_risk)


def supplier_score_from_prediction(prediction: SupplierPrediction) -> Decimal:
    """Scale p_on_time to 0-100, soften by confidence band."""
    base = Decimal(str(prediction.p_on_time)) * Decimal("100")
    if prediction.confidence_band == "low":
        # Pull low-confidence predictions toward an industry-average 70.
        return (base + Decimal("70")) / Decimal("2")
    return base.quantize(Decimal("0.01"))


def commercial_terms_score(
    *,
    price_rank_pct: float,
    has_warranty: bool,
    payment_term_days: int | None,
    fits_window: bool,
) -> Decimal:
    """Lightweight scorer for commercial terms.

    Args:
        price_rank_pct: 0.0 means cheapest among peers, 1.0 means most
          expensive. Cheaper is better.
        has_warranty: true if the quotation declares a warranty
          (>= 6 months).
        payment_term_days: days of payment grace; 0 means cash now.
        fits_window: true if the lead time fits the request's
          fenological / target delivery window.
    """
    price_score = Decimal(str(round((1.0 - max(0.0, min(1.0, price_rank_pct))) * 60.0, 2)))
    warranty_bonus = Decimal("15") if has_warranty else Decimal("0")
    payment_bonus = Decimal("0")
    if payment_term_days is not None:
        if payment_term_days >= 30:
            payment_bonus = Decimal("15")
        elif payment_term_days >= 15:
            payment_bonus = Decimal("8")
        elif payment_term_days <= 0:
            payment_bonus = Decimal("3")
    window_bonus = Decimal("10") if fits_window else Decimal("0")
    score = price_score + warranty_bonus + payment_bonus + window_bonus
    return max(Decimal("0"), min(Decimal("100"), score)).quantize(Decimal("0.01"))


def delivery_risk_score(
    *,
    prediction: SupplierPrediction,
    anomaly: AnomalyResult | None,
    is_imported: bool,
) -> Decimal:
    """Higher means more risky.

    Components:
      - 1 - p_on_time (ML)
      - anomaly_score
      - import bonus (+10 raw points)
    """
    ml_component = (Decimal("1") - Decimal(str(prediction.p_on_time))) * Decimal("70")
    anomaly_component = (
        Decimal(str(anomaly.anomaly_score)) * Decimal("30") if anomaly is not None else Decimal("0")
    )
    import_component = Decimal("10") if is_imported else Decimal("0")
    score = ml_component + anomaly_component + import_component
    return max(Decimal("0"), min(Decimal("100"), score)).quantize(Decimal("0.01"))


def compute_offer_score(components: OfferComponents) -> Decimal:
    score = (
        WEIGHT_SUPPLIER * components.supplier_score
        + WEIGHT_TERMS * components.commercial_terms_score
        + WEIGHT_DELIVERY_INV * (Decimal("100") - components.delivery_risk)
    )
    bounded = max(Decimal("0"), min(Decimal("100"), score))
    return bounded.quantize(Decimal("0.01"))
