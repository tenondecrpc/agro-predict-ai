"""Tests for Phase 4 LLM agents (extractor, comparator, recommender, negotiator).

Each agent is exercised twice:
- LLM disabled: deterministic fallback path produces a valid output.
- LLM stubbed: a canned LLM response flows through the parser.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from backend.llm.adapter import DisabledAdapter
from backend.procurement.agents.comparator import ComparatorAgent
from backend.procurement.agents.extractor import ExtractorAgent
from backend.procurement.agents.negotiator import NegotiatorAgent
from backend.procurement.agents.recommender import RecommenderAgent
from backend.procurement.agents.schemas import (
    ComparisonResult,
    ExtractedQuotation,
    NegotiationMessage,
    Recommendation,
)
from backend.procurement.ml.models import AnomalyResult, SupplierPrediction
from backend.procurement.models import (
    CriteriaWeights,
    PurchaseRequest,
    Quotation,
    QuotationItem,
    QuotationStatus,
    RequestItem,
    Supplier,
)
from backend.procurement.scoring.models import (
    OfferComponents,
    ProcurementScore,
    UrgencyComponents,
)

# ---------------------------------------------------------------------------
# Stubbed LLM
# ---------------------------------------------------------------------------


class _StubLLM:
    def __init__(self, responses: list[str] | str) -> None:
        if isinstance(responses, str):
            self._responses = [responses]
        else:
            self._responses = list(responses)
        self.calls: list[tuple[str, str]] = []

    def complete(self, prompt: str, system: str) -> str:
        self.calls.append((system, prompt))
        return self._responses.pop(0) if self._responses else ""


def _make_request() -> PurchaseRequest:
    return PurchaseRequest(
        tenant_id="tenant-x",
        team_id="team-y",
        requested_by="ana",
        title="Urea 46% para zafra soja 26/27",
        target_crop="soja",
        target_zafra="2026/27",
        fenological_window="pre-siembra",
        delivery_department="Itapua",
        target_delivery_date=date.today() + timedelta(days=30),
        criteria_weights=CriteriaWeights(),
        items=[
            RequestItem(description="Urea granulada 46% N", quantity=Decimal("16000"), unit="kg"),
        ],
    )


def _make_supplier(supplier_id: str, name: str) -> Supplier:
    return Supplier(
        supplier_id=supplier_id,
        tenant_id="tenant-x",
        legal_name=name,
        country="PY",
    )


def _make_quotation(
    supplier_id: str,
    *,
    total: Decimal = Decimal("3375840000"),
    lead_time: int = 10,
    currency: str = "PYG",
    warranty: int | None = 12,
) -> Quotation:
    return Quotation(
        tenant_id="tenant-x",
        request_id="req-1",
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
                description="Urea 46%",
                quantity=Decimal("16000"),
                unit_price=total / Decimal("16000"),
                subtotal=total,
            )
        ],
    )


# ---------------------------------------------------------------------------
# Extractor
# ---------------------------------------------------------------------------


def test_extractor_fallback_when_llm_disabled() -> None:
    raw = "Cotizacion Urea. Total: Gs. 3.375.840.000. Plazo 10 dias. Validez 30 dias."
    agent = ExtractorAgent(DisabledAdapter())
    result = agent.extract(raw, request=_make_request())
    assert isinstance(result, ExtractedQuotation)
    assert result.extraction_source == "fallback"
    assert result.total_amount > Decimal("0")
    assert result.lead_time_days == 10
    assert result.currency == "PYG"


def test_extractor_uses_llm_when_available() -> None:
    response = (
        '{"supplier_legal_name":"Tecnomyl SA","supplier_ruc":"80012345-6",'
        '"currency":"USD","exchange_rate_quoted":7400,"incoterm":"CIF",'
        '"includes_iva":false,"iva_rate":5,"payment_terms":"30 dias",'
        '"total_amount":456000,"lead_time_days":10,'
        '"validity_until_iso":"2027-01-15","warranty_months":12,'
        '"discount_pct":3.5,"items":[{"description":"Urea 46%",'
        '"quantity":16000,"unit_price":28.5,"subtotal":456000,'
        '"presentation":"bolsa 50kg","origin":"Egipto"}],'
        '"extraction_confidence":0.85}'
    )
    agent = ExtractorAgent(_StubLLM(response))
    result = agent.extract("texto cotizacion", request=_make_request())
    assert result.extraction_source == "llm"
    assert result.supplier_legal_name == "Tecnomyl SA"
    assert result.currency == "USD"
    assert result.total_amount == Decimal("456000")
    assert len(result.items) == 1
    assert result.items[0].presentation == "bolsa 50kg"


def test_extractor_falls_back_on_invalid_json() -> None:
    bad = "Sorry, I cannot help with that."
    agent = ExtractorAgent(_StubLLM(bad))
    result = agent.extract("Total Gs. 100", request=_make_request())
    assert result.extraction_source == "fallback"


def test_extractor_handles_markdown_fenced_json() -> None:
    response = (
        '```json\n{"currency":"PYG","total_amount":1000,"lead_time_days":7,'
        '"validity_until_iso":"2027-01-15"}\n```'
    )
    agent = ExtractorAgent(_StubLLM(response))
    result = agent.extract("texto", request=_make_request())
    assert result.extraction_source == "llm"
    assert result.total_amount == Decimal("1000")


# ---------------------------------------------------------------------------
# Comparator
# ---------------------------------------------------------------------------


def test_comparator_fallback_emits_totals_and_best_in_criterion() -> None:
    request = _make_request()
    suppliers = {
        "s1": _make_supplier("s1", "Tecnomyl"),
        "s2": _make_supplier("s2", "Atlantic"),
    }
    quotes = [
        _make_quotation("s1", total=Decimal("3500000000"), lead_time=10, warranty=12),
        _make_quotation("s2", total=Decimal("3200000000"), lead_time=18, warranty=24),
    ]
    agent = ComparatorAgent(DisabledAdapter())
    result = agent.compare(request, quotes, suppliers)
    assert result.source == "fallback"
    assert len(result.totals_by_supplier) == 2
    assert result.best_in_criterion.price == "s2"  # cheapest
    assert result.best_in_criterion.delivery == "s1"  # fastest
    assert result.best_in_criterion.warranty == "s2"
    # 9.4% gap is below 10%, but lead time gap is 8 days >= 7 -> flag
    assert any(d.criterion == "delivery" for d in result.significant_differences)


def test_comparator_uses_llm_when_available() -> None:
    response = (
        '{"items_normalized":[{"request_item_description":"Urea 46%",'
        '"by_supplier":[{"supplier_id":"s1","matched_description":"Urea granular",'
        '"unit_price_pyg":210000,"quantity":16000,"subtotal_pyg":3360000000}]}],'
        '"totals_by_supplier":[{"supplier_id":"s1","supplier_legal_name":"Tecnomyl",'
        '"total_pyg":3360000000,"lead_time_days":10}],'
        '"best_in_criterion":{"price":"s1","delivery":"s1"},'
        '"significant_differences":[]}'
    )
    request = _make_request()
    suppliers = {"s1": _make_supplier("s1", "Tecnomyl")}
    quotes = [_make_quotation("s1")]
    agent = ComparatorAgent(_StubLLM(response))
    result = agent.compare(request, quotes, suppliers)
    assert result.source == "llm"
    assert result.totals_by_supplier[0].total_pyg == Decimal("3360000000")


# ---------------------------------------------------------------------------
# Recommender
# ---------------------------------------------------------------------------


def _make_score(
    quotation_id: str, *, urgency: float, offer: float, band: str = "buy_now"
) -> ProcurementScore:
    return ProcurementScore(
        tenant_id="tenant-x",
        request_id="req-1",
        quotation_id=quotation_id,
        urgency=UrgencyComponents(
            weather_risk=Decimal("70"),
            delivery_urgency=Decimal("70"),
            market_volatility=Decimal("55"),
        ),
        urgency_score=Decimal(str(urgency)),
        offer=OfferComponents(
            supplier_score=Decimal("80"),
            commercial_terms_score=Decimal("75"),
            delivery_risk=Decimal("20"),
        ),
        offer_score=Decimal(str(offer)),
        decision_band=band,  # type: ignore[arg-type]
    )


def test_recommender_fallback_picks_highest_combined_score() -> None:
    request = _make_request()
    quote_a = _make_quotation("s1")
    quote_b = _make_quotation("s2", total=Decimal("4000000000"), lead_time=18)
    quotations_by_id = {quote_a.quotation_id: quote_a, quote_b.quotation_id: quote_b}
    suppliers_by_id = {
        "s1": _make_supplier("s1", "Tecnomyl"),
        "s2": _make_supplier("s2", "Atlantic"),
    }
    scores = [
        _make_score(quote_a.quotation_id, urgency=80, offer=85, band="buy_now"),
        _make_score(quote_b.quotation_id, urgency=70, offer=55, band="negotiate_and_close"),
    ]
    ml = {
        "s1": SupplierPrediction(
            supplier_id="s1", p_on_time=0.92, confidence_band="high",
            based_on_n_observations=20, model_version="rules-v1",
        ),
        "s2": SupplierPrediction(
            supplier_id="s2", p_on_time=0.65, confidence_band="medium",
            based_on_n_observations=8, model_version="rules-v1",
        ),
    }
    anomalies: dict[str, AnomalyResult] = {}
    agent = RecommenderAgent(DisabledAdapter())
    rec = agent.recommend(
        request=request,
        comparison=ComparisonResult(),
        scores=scores,
        quotations_by_id=quotations_by_id,
        suppliers_by_id=suppliers_by_id,
        ml_predictions=ml,
        anomalies=anomalies,
    )
    assert isinstance(rec, Recommendation)
    assert rec.recommended_quotation_id == quote_a.quotation_id
    assert rec.source == "fallback"
    assert "Tecnomyl" in rec.reasoning_markdown
    assert "Recommendation" in rec.reasoning_markdown


def test_recommender_uses_llm_markdown_when_available() -> None:
    response = "## Recommendation: Tecnomyl - Urea\n**Composite score:** 82/100 - **buy_now**\n\n### Justification\n..."
    request = _make_request()
    quote_a = _make_quotation("s1")
    suppliers_by_id = {"s1": _make_supplier("s1", "Tecnomyl")}
    scores = [_make_score(quote_a.quotation_id, urgency=80, offer=85, band="buy_now")]
    agent = RecommenderAgent(_StubLLM(response))
    rec = agent.recommend(
        request=request,
        comparison=ComparisonResult(),
        scores=scores,
        quotations_by_id={quote_a.quotation_id: quote_a},
        suppliers_by_id=suppliers_by_id,
        ml_predictions={
            "s1": SupplierPrediction(
                supplier_id="s1", p_on_time=0.9, confidence_band="high",
                based_on_n_observations=15, model_version="rules-v1",
            )
        },
        anomalies={},
    )
    assert rec.source == "llm"
    assert "Tecnomyl" in rec.reasoning_markdown


# ---------------------------------------------------------------------------
# Negotiator
# ---------------------------------------------------------------------------


def test_negotiator_fallback_emits_spanish_email() -> None:
    request = _make_request()
    supplier = _make_supplier("s1", "Tecnomyl SA")
    quote = _make_quotation("s1")
    agent = NegotiatorAgent(DisabledAdapter())
    msg = agent.draft(
        quotation=quote,
        supplier=supplier,
        request=request,
        best_alternative=None,
        target_improvements={"price_pct": 4, "lead_time_days": 7},
        tone="cordial",
    )
    assert isinstance(msg, NegotiationMessage)
    assert msg.source == "fallback"
    assert "Tecnomyl SA" in msg.message_text
    assert "4%" in msg.message_text
    assert "7 dias" in msg.message_text
    assert "Saludos cordiales" in msg.message_text


def test_negotiator_uses_llm_when_available() -> None:
    response = (
        "Estimado equipo de Tecnomyl,\n\nAgradecemos la cotizacion recibida...\n\n"
        "Saludos cordiales,\n[Nombre del Gerente de Compras]\n[Cooperativa]"
    )
    request = _make_request()
    supplier = _make_supplier("s1", "Tecnomyl SA")
    quote = _make_quotation("s1")
    agent = NegotiatorAgent(_StubLLM(response))
    msg = agent.draft(
        quotation=quote,
        supplier=supplier,
        request=request,
        best_alternative=None,
        target_improvements={"price_pct": 4},
        tone="cordial",
    )
    assert msg.source == "llm"
    assert "Estimado" in msg.message_text


def test_negotiator_falls_back_on_empty_llm_response() -> None:
    request = _make_request()
    supplier = _make_supplier("s1", "Tecnomyl SA")
    quote = _make_quotation("s1")
    agent = NegotiatorAgent(_StubLLM("   "))  # whitespace only
    msg = agent.draft(
        quotation=quote,
        supplier=supplier,
        request=request,
        best_alternative=None,
        target_improvements={},
        tone="cordial",
    )
    assert msg.source == "fallback"
