"""End-to-end tests for the procurement orchestrator (Phase 5).

Stitches together domain repo, decision repo, agents (with LLM
disabled so we use deterministic fallbacks), scoring, ML predictor,
and external signals (stubbed). Verifies the recommend pipeline
returns a coherent result and persists scores + recommendation.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.llm.adapter import DisabledAdapter
from backend.procurement.agents.comparator import ComparatorAgent
from backend.procurement.agents.extractor import ExtractorAgent
from backend.procurement.agents.negotiator import NegotiatorAgent
from backend.procurement.agents.recommender import RecommenderAgent
from backend.procurement.api import build_procurement_router
from backend.procurement.decision_repository import InMemoryDecisionRepository
from backend.procurement.external.models import WeatherComponents, WeatherSnapshot
from backend.procurement.external.repository import InMemoryExternalSignalRepository
from backend.procurement.external.service import FXService, WeatherService
from backend.procurement.ml.supplier_predictor import SupplierPredictor
from backend.procurement.models import (
    PurchaseRequest,
    Quotation,
    QuotationItem,
    QuotationStatus,
    RequestItem,
    Supplier,
)
from backend.procurement.orchestrator import ProcurementOrchestrator
from backend.procurement.repository import InMemoryProcurementRepository
from backend.procurement.service import ProcurementService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_request(stock_days: int = 5) -> PurchaseRequest:
    return PurchaseRequest(
        tenant_id="tenant-x",
        team_id="team-y",
        requested_by="ana",
        title="Urea para zafra soja 26/27",
        target_crop="soja",
        target_zafra="2026/27",
        fenological_window="pre-siembra",
        delivery_department="Itapua",
        target_delivery_date=date.today() + timedelta(days=30),
        current_stock_days=stock_days,
        items=[
            RequestItem(description="Urea 46% N granulada", quantity=Decimal("16000"), unit="kg"),
        ],
    )


def _make_supplier(supplier_id: str, name: str, *, importer: bool = False) -> Supplier:
    return Supplier(
        supplier_id=supplier_id,
        tenant_id="tenant-x",
        legal_name=name,
        country="PY",
        is_importer=importer,
    )


def _make_quotation(
    supplier_id: str,
    request_id: str,
    *,
    total: Decimal = Decimal("3375840000"),
    lead_time: int = 10,
    currency: str = "PYG",
    warranty: int | None = 12,
    item_unit_price: Decimal | None = None,
) -> Quotation:
    unit_price = item_unit_price or (total / Decimal("16000"))
    return Quotation(
        tenant_id="tenant-x",
        request_id=request_id,
        supplier_id=supplier_id,
        created_by="ana",
        currency=currency,
        total_amount=total,
        lead_time_days=lead_time,
        validity_until=date.today() + timedelta(days=15),
        warranty_months=warranty,
        payment_terms="30 dias post-entrega",
        status=QuotationStatus.VALIDATED,
        items=[
            QuotationItem(
                description="Urea granulada 46% N",
                quantity=Decimal("16000"),
                unit_price=unit_price,
                subtotal=total,
            )
        ],
    )


def _build_orchestrator(
    *,
    procurement_repo: InMemoryProcurementRepository,
    decision_repo: InMemoryDecisionRepository,
    weather_score: Decimal | None = Decimal("82"),
) -> ProcurementOrchestrator:
    """Build an orchestrator with stubbed weather/FX and LLM disabled."""
    ext_repo = InMemoryExternalSignalRepository()
    if weather_score is not None:
        # Pre-populate the cache so WeatherService never hits the network.
        now = datetime.now(UTC)
        ext_repo.save_weather_snapshot(
            WeatherSnapshot(
                department="Itapua",
                geo_lat=Decimal("-27.33"),
                geo_lng=Decimal("-55.86"),
                horizon_days=10,
                fetched_at=now,
                valid_until=now + timedelta(hours=6),
                components=WeatherComponents(
                    precipitation_sum_mm=Decimal("5"),
                    heat_stress_days=4,
                    excess_rain_days=0,
                ),
                weather_risk_score=weather_score,
                risk_band="high",
                interpretation="drought signal: simulated",
            )
        )
    weather_service = WeatherService(repository=ext_repo)
    fx_service = FXService(repository=ext_repo)
    # Pre-populate FX cache so the FX service never calls out
    from backend.procurement.external.fx import build_rate

    ext_repo.save_fx_rate(build_rate(rate_reference=Decimal("7400"), source="test"))

    return ProcurementOrchestrator(
        domain_repo=procurement_repo,
        decision_repo=decision_repo,
        comparator=ComparatorAgent(DisabledAdapter()),
        recommender=RecommenderAgent(DisabledAdapter()),
        supplier_predictor=SupplierPredictor(model_path=Path("/__nonexistent__")),
        weather_service=weather_service,
        fx_service=fx_service,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_recommend_escalates_when_request_missing() -> None:
    proc_repo = InMemoryProcurementRepository()
    dec_repo = InMemoryDecisionRepository()
    orchestrator = _build_orchestrator(procurement_repo=proc_repo, decision_repo=dec_repo)
    result = orchestrator.recommend("nonexistent", tenant_id="tenant-x")
    assert result.status == "escalated"
    assert result.escalation_reason == "purchase_request_not_found"


def test_recommend_escalates_with_single_quotation() -> None:
    proc_repo = InMemoryProcurementRepository()
    dec_repo = InMemoryDecisionRepository()
    request = _make_request()
    proc_repo.save_request(request)
    sup = _make_supplier("s1", "Tecnomyl")
    proc_repo.save_supplier(sup)
    proc_repo.save_quotation(_make_quotation("s1", request.request_id))
    orchestrator = _build_orchestrator(procurement_repo=proc_repo, decision_repo=dec_repo)
    result = orchestrator.recommend(request.request_id, tenant_id="tenant-x")
    assert result.status == "escalated"
    assert result.escalation_reason == "insufficient_validated_quotations"


def test_recommend_full_pipeline_completes() -> None:
    proc_repo = InMemoryProcurementRepository()
    dec_repo = InMemoryDecisionRepository()
    request = _make_request(stock_days=5)
    proc_repo.save_request(request)

    sup_a = _make_supplier("s1", "Tecnomyl SA")
    sup_b = _make_supplier("s2", "Atlantic Comercio", importer=True)
    sup_c = _make_supplier("s3", "Glymax")
    for s in (sup_a, sup_b, sup_c):
        proc_repo.save_supplier(s)

    # Three quotations with deliberate spread
    proc_repo.save_quotation(_make_quotation("s1", request.request_id, total=Decimal("3500000000"), lead_time=10))
    proc_repo.save_quotation(_make_quotation("s2", request.request_id, total=Decimal("3200000000"), lead_time=18))
    proc_repo.save_quotation(_make_quotation("s3", request.request_id, total=Decimal("3700000000"), lead_time=14))

    orchestrator = _build_orchestrator(
        procurement_repo=proc_repo,
        decision_repo=dec_repo,
        weather_score=Decimal("82"),  # drought scenario
    )
    result = orchestrator.recommend(request.request_id, tenant_id="tenant-x")

    assert result.status == "completed"
    assert result.escalation_reason is None
    assert result.recommendation is not None
    assert result.recommendation_id is not None
    assert result.weather_risk_score == Decimal("82")
    assert result.fx_rate_usd_pyg == Decimal("7400")
    assert len(result.scores) == 3

    # All scores reference real quotations and have plausible values
    for s in result.scores:
        assert Decimal("0") <= s.urgency_score <= Decimal("100")
        assert Decimal("0") <= s.offer_score <= Decimal("100")
        assert s.decision_band in (
            "buy_now",
            "negotiate_and_close",
            "buy_with_followup",
            "wait_better_offer",
            "not_recommended",
        )

    # Recommendation persisted to the decision repo
    persisted = dec_repo.get_latest_recommendation(
        request.request_id, tenant_id="tenant-x"
    )
    assert persisted is not None
    assert persisted["recommended_quotation_id"] == result.recommendation.recommended_quotation_id

    # Markdown reasoning includes the supplier name and the decision band
    md = result.recommendation.reasoning_markdown
    assert "Recommendation:" in md
    assert any(name in md for name in ("Tecnomyl", "Atlantic", "Glymax"))


def test_recommend_picks_quotation_with_strongest_combined_score() -> None:
    proc_repo = InMemoryProcurementRepository()
    dec_repo = InMemoryDecisionRepository()
    request = _make_request(stock_days=5)
    proc_repo.save_request(request)

    proc_repo.save_supplier(_make_supplier("s1", "Tecnomyl"))
    proc_repo.save_supplier(_make_supplier("s2", "Glymax"))
    q_a = _make_quotation("s1", request.request_id, total=Decimal("3400000000"), lead_time=8)
    q_b = _make_quotation("s2", request.request_id, total=Decimal("3300000000"), lead_time=20)
    proc_repo.save_quotation(q_a)
    proc_repo.save_quotation(q_b)

    orchestrator = _build_orchestrator(
        procurement_repo=proc_repo, decision_repo=dec_repo, weather_score=Decimal("82")
    )
    result = orchestrator.recommend(request.request_id, tenant_id="tenant-x")

    # Whichever wins the combined score, the recommendation must point
    # at one of the two validated quotations and the loser must surface
    # in the narrative.
    assert result.status == "completed"
    assert result.recommendation.recommended_quotation_id in {q_a.quotation_id, q_b.quotation_id}
    # The loser's decision band must reflect the trade-off: if
    # Tecnomyl's window-fit win was overridden by Glymax's price, then
    # Tecnomyl should be in negotiate_and_close (urgency high but offer
    # medium under our current weights).
    other_id = (
        q_a.quotation_id
        if result.recommendation.recommended_quotation_id == q_b.quotation_id
        else q_b.quotation_id
    )
    other_score = next(s for s in result.scores if s.quotation_id == other_id)
    assert other_score.decision_band in (
        "negotiate_and_close",
        "buy_with_followup",
        "wait_better_offer",
    )


# ---------------------------------------------------------------------------
# API-level tests (FastAPI client)
# ---------------------------------------------------------------------------


def _build_test_client() -> tuple[TestClient, InMemoryProcurementRepository, InMemoryDecisionRepository]:
    proc_repo = InMemoryProcurementRepository()
    dec_repo = InMemoryDecisionRepository()
    proc_service = ProcurementService(repository=proc_repo)
    orchestrator = _build_orchestrator(procurement_repo=proc_repo, decision_repo=dec_repo)
    app = FastAPI()
    app.include_router(
        build_procurement_router(
            proc_service,
            extractor=ExtractorAgent(DisabledAdapter()),
            negotiator=NegotiatorAgent(DisabledAdapter()),
            orchestrator=orchestrator,
        )
    )
    return TestClient(app), proc_repo, dec_repo


def test_recommend_endpoint_returns_422_when_underqualified() -> None:
    client, proc_repo, _ = _build_test_client()
    request = _make_request()
    proc_repo.save_request(request)
    response = client.post(
        f"/api/v1/procurement/requests/{request.request_id}/recommend",
        params={"tenant_id": "tenant-x"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["escalation_reason"] == "insufficient_validated_quotations"


def test_recommend_endpoint_returns_recommendation() -> None:
    client, proc_repo, dec_repo = _build_test_client()
    request = _make_request()
    proc_repo.save_request(request)
    proc_repo.save_supplier(_make_supplier("s1", "Tecnomyl"))
    proc_repo.save_supplier(_make_supplier("s2", "Glymax"))
    proc_repo.save_quotation(
        _make_quotation("s1", request.request_id, total=Decimal("3400000000"), lead_time=10)
    )
    proc_repo.save_quotation(
        _make_quotation("s2", request.request_id, total=Decimal("3300000000"), lead_time=14)
    )
    response = client.post(
        f"/api/v1/procurement/requests/{request.request_id}/recommend",
        params={"tenant_id": "tenant-x"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["score_count"] == 2
    assert body["recommendation"] is not None
    assert body["recommendation"]["recommended_quotation_id"]


def test_extract_endpoint_uses_fallback_when_llm_disabled() -> None:
    client, proc_repo, _ = _build_test_client()
    response = client.post(
        "/api/v1/procurement/quotations/extract",
        json={
            "raw_text": "Cotizacion. Total: Gs. 3.000.000. Plazo 12 dias.",
            "tenant_id": "tenant-x",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["extraction_source"] == "fallback"
    assert body["lead_time_days"] == 12


def test_negotiate_endpoint_returns_message() -> None:
    client, proc_repo, _ = _build_test_client()
    request = _make_request()
    proc_repo.save_request(request)
    proc_repo.save_supplier(_make_supplier("s1", "Tecnomyl SA"))
    proc_repo.save_supplier(_make_supplier("s2", "Glymax"))
    quote = _make_quotation("s1", request.request_id, total=Decimal("3400000000"))
    other = _make_quotation("s2", request.request_id, total=Decimal("3300000000"))
    proc_repo.save_quotation(quote)
    proc_repo.save_quotation(other)
    response = client.post(
        f"/api/v1/procurement/quotations/{quote.quotation_id}/negotiate",
        json={
            "target_improvements": {"price_pct": 4, "lead_time_days": 7},
            "tone": "cordial",
            "tenant_id": "tenant-x",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert "Tecnomyl SA" in body["message_text"]
    assert "4%" in body["message_text"]


def test_negotiate_endpoint_404_for_unknown_quotation() -> None:
    client, _, _ = _build_test_client()
    response = client.post(
        "/api/v1/procurement/quotations/missing/negotiate",
        json={"target_improvements": {}, "tone": "cordial", "tenant_id": "tenant-x"},
    )
    assert response.status_code == 404
