"""Decision matrix mapping (urgency, offer) to a recommendation band.

| Urgency  | Offer     | Decision                  |
|----------|-----------|---------------------------|
| high     | high      | buy_now                   |
| high     | medium    | negotiate_and_close       |
| medium   | high      | buy_with_followup         |
| low      | low       | wait_better_offer         |
| any      | very low  | not_recommended           |
| else     | else      | wait_better_offer         |

Thresholds:
  - urgency: high >= 70, medium 40-69, low < 40
  - offer:   very_low < 25, low < 40, medium 40-69, high >= 70

This is the core textual contract the LLM Recommender wraps in narrative.
"""

from __future__ import annotations

from decimal import Decimal

from backend.procurement.scoring.models import DecisionBand

URGENCY_HIGH = Decimal("70")
URGENCY_MEDIUM = Decimal("40")
OFFER_VERY_LOW = Decimal("25")
OFFER_LOW = Decimal("40")
OFFER_HIGH = Decimal("70")


def _urgency_tier(score: Decimal) -> str:
    if score >= URGENCY_HIGH:
        return "high"
    if score >= URGENCY_MEDIUM:
        return "medium"
    return "low"


def _offer_tier(score: Decimal) -> str:
    if score < OFFER_VERY_LOW:
        return "very_low"
    if score < OFFER_LOW:
        return "low"
    if score < OFFER_HIGH:
        return "medium"
    return "high"


def decide(urgency_score: Decimal, offer_score: Decimal) -> DecisionBand:
    offer_tier = _offer_tier(offer_score)
    if offer_tier == "very_low":
        return "not_recommended"
    urgency_tier = _urgency_tier(urgency_score)
    if urgency_tier == "high" and offer_tier == "high":
        return "buy_now"
    if urgency_tier == "high" and offer_tier == "medium":
        return "negotiate_and_close"
    if urgency_tier == "medium" and offer_tier == "high":
        return "buy_with_followup"
    if urgency_tier == "low" and offer_tier == "low":
        return "wait_better_offer"
    return "wait_better_offer"
