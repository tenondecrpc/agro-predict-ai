"""Tests for Phase 3: scoring + ML supplier predictor + anomaly.

All tests are deterministic and run without network or DB.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from backend.procurement.ml.anomaly_detector import CatalogBand, evaluate_anomaly
from backend.procurement.ml.features import extract_features
from backend.procurement.ml.models import SupplierPerformanceRecord, SupplierPrediction
from backend.procurement.ml.supplier_predictor import SupplierPredictor
from backend.procurement.scoring import (
    OfferComponents,
    UrgencyComponents,
    commercial_terms_score,
    compute_offer_score,
    compute_urgency_score,
    decide,
    delivery_risk_score,
    delivery_urgency_from_stock,
    supplier_score_from_prediction,
    volatility_score,
)

# ---------------------------------------------------------------------------
# Urgency Score
# ---------------------------------------------------------------------------


def test_urgency_score_drought_with_low_stock_is_high() -> None:
    components = UrgencyComponents(
        weather_risk=Decimal("90"),
        delivery_urgency=delivery_urgency_from_stock(5),
        market_volatility=volatility_score("high"),
    )
    score = compute_urgency_score(components)
    # 0.45*90 + 0.40*95 + 0.15*85 = 40.5 + 38 + 12.75 = 91.25
    assert score == Decimal("91.25")


def test_urgency_score_neutral_weather_with_stock_is_low() -> None:
    components = UrgencyComponents(
        weather_risk=Decimal("20"),
        delivery_urgency=delivery_urgency_from_stock(30),
        market_volatility=volatility_score("low"),
    )
    score = compute_urgency_score(components)
    # 0.45*20 + 0.40*35 + 0.15*25 = 9 + 14 + 3.75 = 26.75
    assert score == Decimal("26.75")


def test_delivery_urgency_buckets() -> None:
    assert delivery_urgency_from_stock(3) == Decimal("95")
    assert delivery_urgency_from_stock(10) == Decimal("70")
    assert delivery_urgency_from_stock(30) == Decimal("35")
    assert delivery_urgency_from_stock(None) == Decimal("50")


# ---------------------------------------------------------------------------
# Offer Score
# ---------------------------------------------------------------------------


def test_commercial_terms_rewards_cheap_with_warranty_and_payment() -> None:
    score = commercial_terms_score(
        price_rank_pct=0.0,  # cheapest
        has_warranty=True,
        payment_term_days=30,
        fits_window=True,
    )
    # 0.0 -> 60, +15 warranty, +15 payment, +10 window = 100
    assert score == Decimal("100")


def test_commercial_terms_punishes_expensive_no_warranty() -> None:
    score = commercial_terms_score(
        price_rank_pct=1.0,
        has_warranty=False,
        payment_term_days=0,
        fits_window=False,
    )
    # 0.0 (price) + 0 + 3 (cash) + 0 = 3
    assert score == Decimal("3")


def test_offer_score_high_supplier_with_good_terms_is_high() -> None:
    components = OfferComponents(
        supplier_score=Decimal("90"),
        commercial_terms_score=Decimal("85"),
        delivery_risk=Decimal("20"),
    )
    # 0.35*90 + 0.40*85 + 0.25*(100-20) = 31.5 + 34 + 20 = 85.5
    score = compute_offer_score(components)
    assert score == Decimal("85.50")


# ---------------------------------------------------------------------------
# Decision matrix
# ---------------------------------------------------------------------------


def test_decision_buy_now_when_both_high() -> None:
    assert decide(Decimal("80"), Decimal("85")) == "buy_now"


def test_decision_negotiate_when_urgent_but_offer_medium() -> None:
    assert decide(Decimal("80"), Decimal("55")) == "negotiate_and_close"


def test_decision_buy_with_followup_when_medium_urgency_high_offer() -> None:
    assert decide(Decimal("55"), Decimal("80")) == "buy_with_followup"


def test_decision_wait_when_both_low() -> None:
    assert decide(Decimal("20"), Decimal("30")) == "wait_better_offer"


def test_decision_not_recommended_when_offer_very_low() -> None:
    assert decide(Decimal("90"), Decimal("15")) == "not_recommended"


# ---------------------------------------------------------------------------
# Supplier predictor (rules + trained)
# ---------------------------------------------------------------------------


def _make_history(
    supplier_id: str,
    on_time_count: int,
    late_count: int,
    *,
    delay_per_late: int = 2,
) -> list[SupplierPerformanceRecord]:
    today = date.today()
    records: list[SupplierPerformanceRecord] = []
    for i in range(on_time_count):
        records.append(
            SupplierPerformanceRecord(
                tenant_id="t",
                supplier_id=supplier_id,
                category="fertilizante",
                awarded_date=today - timedelta(days=30 + i * 15),
                promised_delivery_date=today - timedelta(days=20 + i * 15),
                actual_delivery_date=today - timedelta(days=20 + i * 15),
                delivered_on_time=True,
                days_delay=0,
            )
        )
    for i in range(late_count):
        records.append(
            SupplierPerformanceRecord(
                tenant_id="t",
                supplier_id=supplier_id,
                category="fertilizante",
                awarded_date=today - timedelta(days=10 + i * 15),
                promised_delivery_date=today - timedelta(days=5 + i * 15),
                actual_delivery_date=today + timedelta(days=delay_per_late - i * 15),
                delivered_on_time=False,
                days_delay=delay_per_late,
            )
        )
    return records


def test_predictor_supplier_with_strong_history_returns_high_p() -> None:
    history = _make_history("strong-supplier", on_time_count=10, late_count=1)
    predictor = SupplierPredictor(model_path=Path("/__nonexistent__"))  # force rules-based fallback for determinism
    result = predictor.predict_for_supplier("strong-supplier", history)
    assert isinstance(result, SupplierPrediction)
    assert result.based_on_n_observations == 11
    assert result.p_on_time >= 0.7
    assert result.confidence_band in ("medium", "high")


def test_predictor_supplier_with_chronic_delays_returns_lower_p() -> None:
    history = _make_history("weak-supplier", on_time_count=2, late_count=8, delay_per_late=8)
    predictor = SupplierPredictor(model_path=Path("/__nonexistent__"))
    result = predictor.predict_for_supplier("weak-supplier", history)
    assert result.p_on_time <= 0.6


def test_predictor_with_no_history_returns_neutral_p() -> None:
    predictor = SupplierPredictor(model_path=Path("/__nonexistent__"))
    result = predictor.predict_for_supplier("unknown-supplier", [])
    assert result.based_on_n_observations == 0
    assert 0.4 <= result.p_on_time <= 0.8


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------


def test_features_extraction_counts_recent_observations() -> None:
    history = _make_history("s1", on_time_count=4, late_count=2)
    features = extract_features("s1", history)
    assert features.n_observations == 6
    assert features.on_time_rate_all > 0.5
    assert 0 <= features.on_time_rate_last_3 <= 1.0


# ---------------------------------------------------------------------------
# Anomaly detector
# ---------------------------------------------------------------------------


def test_anomaly_flagged_when_below_band() -> None:
    band = CatalogBand("urea", Decimal("380"), Decimal("460"))
    result = evaluate_anomaly(
        quotation_id="q1",
        unit_price_usd=Decimal("280"),  # 23% below min
        band=band,
    )
    assert result.flagged is True
    assert result.anomaly_score >= 0.6
    assert "below" in (result.reason or "")


def test_anomaly_flagged_when_above_band() -> None:
    band = CatalogBand("urea", Decimal("380"), Decimal("460"))
    result = evaluate_anomaly(
        quotation_id="q1",
        unit_price_usd=Decimal("600"),
        band=band,
    )
    assert result.flagged is True
    assert "above" in (result.reason or "")


def test_anomaly_inside_band_is_low_score() -> None:
    band = CatalogBand("urea", Decimal("380"), Decimal("460"))
    result = evaluate_anomaly(
        quotation_id="q1",
        unit_price_usd=Decimal("420"),
        band=band,
    )
    assert result.flagged is False
    assert result.anomaly_score < 0.4


# ---------------------------------------------------------------------------
# Glue: ML output -> Offer Score
# ---------------------------------------------------------------------------


def test_supplier_score_from_prediction_pulls_low_confidence_to_neutral() -> None:
    low_conf = SupplierPrediction(
        supplier_id="s1",
        p_on_time=0.40,
        confidence_band="low",
        based_on_n_observations=1,
        model_version="rules-v1",
    )
    score = supplier_score_from_prediction(low_conf)
    # 40 -> averaged with 70 -> 55
    assert Decimal("50") <= score <= Decimal("60")


def test_delivery_risk_combines_ml_and_anomaly() -> None:
    pred = SupplierPrediction(
        supplier_id="s1",
        p_on_time=0.50,
        confidence_band="medium",
        based_on_n_observations=8,
        model_version="rules-v1",
    )
    risk_no_anomaly = delivery_risk_score(prediction=pred, anomaly=None, is_imported=False)
    risk_with_anomaly = delivery_risk_score(
        prediction=pred,
        anomaly=type(
            "MockAnomaly",
            (),
            {"anomaly_score": 0.85},
        )(),  # type: ignore[arg-type]
        is_imported=True,
    )
    assert risk_with_anomaly > risk_no_anomaly
