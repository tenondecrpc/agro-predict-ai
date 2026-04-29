"""Price anomaly detector.

Compares each item in a quotation to the published market band stored
in ``procurement_agro_catalog`` for its category. Returns a normalized
anomaly score in [0, 1] and a textual reason.

Two complementary checks:

1. **Range check.** If the item unit price (in USD-equivalent) falls
   outside the published [min, max] band for the category, flag it.
   The further outside, the higher the score.
2. **Z-score check.** When historical samples are available, compute
   the deviation in standard-deviation units relative to peer
   quotations of the same category. >2 sigma flags.

The MVP uses range checks alone since the catalog already encodes
expected bands. The z-score path can be enabled later once we have
enough historical award data.
"""

from __future__ import annotations

from decimal import Decimal

from backend.procurement.ml.models import AnomalyResult


class CatalogBand:
    __slots__ = ("category", "min_usd", "max_usd")

    def __init__(self, category: str, min_usd: Decimal, max_usd: Decimal) -> None:
        self.category = category
        self.min_usd = min_usd
        self.max_usd = max_usd


def evaluate_anomaly(
    *,
    quotation_id: str,
    unit_price_usd: Decimal | None,
    band: CatalogBand | None,
) -> AnomalyResult:
    if unit_price_usd is None or band is None:
        return AnomalyResult(
            quotation_id=quotation_id,
            anomaly_score=0.0,
            z_score_max=0.0,
            flagged=False,
            reason="no catalog band or price available",
            category_checked=band.category if band else None,
            expected_min_usd=band.min_usd if band else None,
            expected_max_usd=band.max_usd if band else None,
            observed_unit_price_usd=unit_price_usd,
        )

    midpoint = (band.min_usd + band.max_usd) / Decimal("2")
    half_range = max((band.max_usd - band.min_usd) / Decimal("2"), Decimal("0.01"))
    deviation = unit_price_usd - midpoint
    # z-score-like: 1.0 means right at the band edge, 2.0 is one full
    # half-range outside. We cap at 5 to avoid runaway scores.
    z_value = float(abs(deviation) / half_range)
    z_value = min(z_value, 5.0)

    flagged = unit_price_usd < band.min_usd or unit_price_usd > band.max_usd
    if flagged:
        # Map z [1, 5] -> score [0.6, 1.0]
        score = 0.6 + (min(z_value, 5.0) - 1.0) * (0.4 / 4.0)
        score = max(0.6, min(1.0, score))
    else:
        # Inside the band -> low anomaly. Score scales 0..0.4 with z in [0, 1).
        score = max(0.0, min(0.4, z_value * 0.4))

    if unit_price_usd < band.min_usd:
        reason = (
            f"unit price USD {unit_price_usd} is {z_value:.2f}x half-range below market "
            f"min for category '{band.category}' (expected USD {band.min_usd}-{band.max_usd}). "
            "Verify product specs - possible substitution, distressed stock, or bait pricing."
        )
    elif unit_price_usd > band.max_usd:
        reason = (
            f"unit price USD {unit_price_usd} is {z_value:.2f}x half-range above market "
            f"max for category '{band.category}' (expected USD {band.min_usd}-{band.max_usd}). "
            "Likely premium product or supply-chain markup."
        )
    else:
        reason = "inside expected market band"

    return AnomalyResult(
        quotation_id=quotation_id,
        anomaly_score=round(score, 3),
        z_score_max=round(z_value, 3),
        flagged=flagged,
        reason=reason,
        category_checked=band.category,
        expected_min_usd=band.min_usd,
        expected_max_usd=band.max_usd,
        observed_unit_price_usd=unit_price_usd,
    )
