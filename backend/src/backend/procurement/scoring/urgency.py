"""Urgency Score: 'should I buy now or can I wait?'

Formula (per ``compras/COMPRAS_AGRO_plan.md``):

    urgency = 0.45 * weather_risk
            + 0.40 * delivery_urgency
            + 0.15 * market_volatility

All inputs are 0-100; the output is a Decimal in the same range.
"""

from __future__ import annotations

from decimal import Decimal

from backend.procurement.scoring.models import UrgencyComponents, VolatilityLevel

WEIGHT_WEATHER = Decimal("0.45")
WEIGHT_DELIVERY = Decimal("0.40")
WEIGHT_VOLATILITY = Decimal("0.15")

VOLATILITY_VALUES: dict[VolatilityLevel, Decimal] = {
    "low": Decimal("25"),
    "medium": Decimal("55"),
    "high": Decimal("85"),
}


def delivery_urgency_from_stock(stock_days: int | None) -> Decimal:
    """Map stock cover days to a delivery urgency score (0-100).

    Calibration from the plan:
      < 7 days  -> 95
      7-15 days -> 70
      > 15 days -> 35
    """
    if stock_days is None:
        return Decimal("50")
    if stock_days < 7:
        return Decimal("95")
    if stock_days <= 15:
        return Decimal("70")
    return Decimal("35")


def volatility_score(level: VolatilityLevel | None) -> Decimal:
    if level is None:
        return Decimal("40")
    return VOLATILITY_VALUES.get(level, Decimal("40"))


def compute_urgency_score(components: UrgencyComponents) -> Decimal:
    score = (
        WEIGHT_WEATHER * components.weather_risk
        + WEIGHT_DELIVERY * components.delivery_urgency
        + WEIGHT_VOLATILITY * components.market_volatility
    )
    # Bound and round to two decimals.
    bounded = max(Decimal("0"), min(Decimal("100"), score))
    return bounded.quantize(Decimal("0.01"))
