"""End-to-end procurement decision orchestrator (spec 019).

Plays the role of ``ProcurementGraph`` from the plan. Vanilla Python
sequence rather than a LangGraph StateGraph because the procurement
recommend pipeline is short, synchronous, and does not need
checkpointing for the demo. The repo's existing ``PredictionGraph``
shows the LangGraph pattern; we can swap to it later without
changing the public API.

Pipeline (spec 019):

    load -> compute_scores -> compare (LLM) -> recommend (LLM)
         -> review -> persist

Failures route to an explicit ``escalation_reason`` rather than
raising into the API layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from backend.procurement.agents.comparator import ComparatorAgent
from backend.procurement.agents.recommender import RecommenderAgent
from backend.procurement.agents.schemas import ComparisonResult, Recommendation
from backend.procurement.decision_repository import DecisionRepository
from backend.procurement.external.service import FXService, WeatherService
from backend.procurement.ml.anomaly_detector import CatalogBand, evaluate_anomaly
from backend.procurement.ml.models import AnomalyResult, SupplierPrediction
from backend.procurement.ml.supplier_predictor import SupplierPredictor
from backend.procurement.models import PurchaseRequest, Quotation, Supplier
from backend.procurement.repository import ProcurementRepository
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
from backend.procurement.scoring.models import ProcurementScore, VolatilityLevel

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Aggregated output of the full recommend pipeline."""

    request_id: str
    tenant_id: str
    status: Literal["completed", "escalated"]
    escalation_reason: str | None = None
    comparison: ComparisonResult | None = None
    scores: list[ProcurementScore] = field(default_factory=list)
    recommendation: Recommendation | None = None
    recommendation_id: str | None = None
    weather_risk_score: Decimal | None = None
    fx_rate_usd_pyg: Decimal | None = None


class ProcurementOrchestrator:
    """Coordinates agents, scorers, and persistence to produce a recommendation."""

    def __init__(
        self,
        *,
        domain_repo: ProcurementRepository,
        decision_repo: DecisionRepository,
        comparator: ComparatorAgent,
        recommender: RecommenderAgent,
        supplier_predictor: SupplierPredictor,
        weather_service: WeatherService | None = None,
        fx_service: FXService | None = None,
        catalog_bands: dict[str, CatalogBand] | None = None,
    ) -> None:
        self._domain = domain_repo
        self._decisions = decision_repo
        self._comparator = comparator
        self._recommender = recommender
        self._predictor = supplier_predictor
        self._weather = weather_service
        self._fx = fx_service
        self._bands = catalog_bands or _DEFAULT_BANDS

    # ------------------------------------------------------------------
    def recommend(
        self,
        request_id: str,
        *,
        tenant_id: str,
        volatility: VolatilityLevel | None = "medium",
    ) -> PipelineResult:
        result = PipelineResult(request_id=request_id, tenant_id=tenant_id, status="escalated")

        # 1. Load
        request = self._domain.get_request(request_id, tenant_id=tenant_id)
        if request is None:
            result.escalation_reason = "purchase_request_not_found"
            return result
        quotations = self._domain.list_quotations_for_request(
            request_id, tenant_id=tenant_id, only_validated=True
        )
        if len(quotations) < 2:
            result.escalation_reason = "insufficient_validated_quotations"
            return result

        suppliers_by_id: dict[str, Supplier] = {}
        for q in quotations:
            sup = self._domain.get_supplier(q.supplier_id, tenant_id=tenant_id)
            if sup is not None:
                suppliers_by_id[q.supplier_id] = sup

        # 2. External signals
        weather_score = self._fetch_weather_score(request)
        result.weather_risk_score = weather_score
        fx_rate = self._fetch_fx_rate()
        result.fx_rate_usd_pyg = fx_rate

        # 3. ML predictions per supplier (per-tenant history is loaded
        # from the domain repo if available; tests inject empty history).
        ml_predictions = self._predict_suppliers(quotations)

        # 4. Anomaly detection per quotation
        anomalies = self._evaluate_anomalies(quotations, fx_rate=fx_rate)

        # 5. Compute scores per quotation
        scores = self._compute_scores(
            request=request,
            quotations=quotations,
            suppliers=suppliers_by_id,
            weather_risk=weather_score,
            volatility=volatility,
            ml_predictions=ml_predictions,
            anomalies=anomalies,
            tenant_id=tenant_id,
        )
        for s in scores:
            try:
                self._decisions.save_score(s)
            except Exception:  # noqa: BLE001
                logger.exception("failed to persist score for quotation %s", s.quotation_id)
        result.scores = scores

        # 6. Compare (LLM agent)
        comparison = self._comparator.compare(
            request, quotations, suppliers_by_id, fx_rate_usd_pyg=fx_rate
        )
        result.comparison = comparison

        # 7. Recommend (LLM agent)
        quotations_by_id = {q.quotation_id: q for q in quotations}
        recommendation = self._recommender.recommend(
            request=request,
            comparison=comparison,
            scores=scores,
            quotations_by_id=quotations_by_id,
            suppliers_by_id=suppliers_by_id,
            ml_predictions=ml_predictions,
            anomalies=anomalies,
        )

        # 8. Review (sanity-check the recommendation references real records)
        if recommendation.recommended_quotation_id not in quotations_by_id:
            result.escalation_reason = "recommendation_references_unknown_quotation"
            return result

        # 9. Persist
        try:
            rec_id = self._decisions.save_recommendation(
                recommendation,
                tenant_id=tenant_id,
                request_id=request_id,
            )
            result.recommendation_id = rec_id
        except Exception:  # noqa: BLE001
            logger.exception("failed to persist recommendation")
            # Non-fatal: return the recommendation even if persistence failed.

        result.recommendation = recommendation
        result.status = "completed"
        return result

    # ------------------------------------------------------------------
    def _fetch_weather_score(self, request: PurchaseRequest) -> Decimal:
        if self._weather is None or not request.delivery_department:
            return Decimal("40")  # neutral default
        try:
            snapshot = self._weather.get_or_fetch(
                department=request.delivery_department, horizon_days=10
            )
            return snapshot.weather_risk_score
        except Exception as exc:  # noqa: BLE001
            logger.warning("weather fetch failed: %s; using neutral default", exc)
            return Decimal("40")

    def _fetch_fx_rate(self) -> Decimal | None:
        if self._fx is None:
            return None
        try:
            return self._fx.get_or_fetch(base="USD", quote="PYG").rate_reference
        except Exception as exc:  # noqa: BLE001
            logger.warning("fx fetch failed: %s", exc)
            return None

    def _predict_suppliers(
        self, quotations: list[Quotation]
    ) -> dict[str, SupplierPrediction]:
        predictions: dict[str, SupplierPrediction] = {}
        seen: set[str] = set()
        for q in quotations:
            if q.supplier_id in seen:
                continue
            seen.add(q.supplier_id)
            history = self._load_history(q.supplier_id)
            predictions[q.supplier_id] = self._predictor.predict_for_supplier(
                q.supplier_id, history
            )
        return predictions

    def _load_history(self, supplier_id: str) -> list:
        if not hasattr(self._decisions, "list_history_for_supplier"):
            return []
        try:
            return self._decisions.list_history_for_supplier(supplier_id, limit=50)
        except Exception:  # noqa: BLE001
            logger.exception("failed to load supplier history for %s", supplier_id)
            return []

    def _evaluate_anomalies(
        self, quotations: list[Quotation], *, fx_rate: Decimal | None
    ) -> dict[str, AnomalyResult]:
        out: dict[str, AnomalyResult] = {}
        for q in quotations:
            if not q.items:
                continue
            unit_price_usd = self._unit_price_usd(q, fx_rate=fx_rate)
            band = self._guess_band_for_quotation(q)
            out[q.quotation_id] = evaluate_anomaly(
                quotation_id=q.quotation_id,
                unit_price_usd=unit_price_usd,
                band=band,
            )
        return out

    @staticmethod
    def _unit_price_usd(q: Quotation, *, fx_rate: Decimal | None) -> Decimal | None:
        if not q.items:
            return None
        unit_price = q.items[0].unit_price
        if q.currency == "USD":
            return unit_price
        if q.currency == "PYG" and fx_rate and fx_rate > 0:
            return (unit_price / fx_rate).quantize(Decimal("0.0001"))
        return None

    def _guess_band_for_quotation(self, q: Quotation) -> CatalogBand | None:
        if not q.items:
            return None
        description = q.items[0].description.lower()
        for keyword, band in self._bands.items():
            if keyword in description:
                return band
        return None

    def _compute_scores(
        self,
        *,
        request: PurchaseRequest,
        quotations: list[Quotation],
        suppliers: dict[str, Supplier],
        weather_risk: Decimal,
        volatility: VolatilityLevel | None,
        ml_predictions: dict[str, SupplierPrediction],
        anomalies: dict[str, AnomalyResult],
        tenant_id: str,
    ) -> list[ProcurementScore]:
        out: list[ProcurementScore] = []
        delivery_urgency = delivery_urgency_from_stock(request.current_stock_days)
        vol_score = volatility_score(volatility)
        urgency_components = UrgencyComponents(
            weather_risk=weather_risk,
            delivery_urgency=delivery_urgency,
            market_volatility=vol_score,
        )
        urgency_score = compute_urgency_score(urgency_components)

        # Build a price ranking among the validated quotations.
        normalized_totals: list[tuple[str, Decimal]] = []
        for q in quotations:
            total = q.total_pyg_normalized or q.total_amount
            normalized_totals.append((q.quotation_id, total))
        sorted_quotes = sorted(normalized_totals, key=lambda x: x[1])
        rank_pct: dict[str, float] = {}
        n = len(sorted_quotes)
        for i, (qid, _) in enumerate(sorted_quotes):
            rank_pct[qid] = i / max(n - 1, 1)

        for q in quotations:
            sup = suppliers.get(q.supplier_id)
            pred = ml_predictions.get(q.supplier_id)
            if pred is None:
                continue
            anomaly = anomalies.get(q.quotation_id)
            sup_score = supplier_score_from_prediction(pred)
            terms = commercial_terms_score(
                price_rank_pct=rank_pct.get(q.quotation_id, 0.5),
                has_warranty=bool(q.warranty_months and q.warranty_months >= 6),
                payment_term_days=_extract_payment_days(q.payment_terms),
                fits_window=q.lead_time_days <= 14,
            )
            risk = delivery_risk_score(
                prediction=pred,
                anomaly=anomaly,
                is_imported=bool(sup and sup.is_importer),
            )
            offer_components = OfferComponents(
                supplier_score=sup_score,
                commercial_terms_score=terms,
                delivery_risk=risk,
            )
            offer_score = compute_offer_score(offer_components)
            band = decide(urgency_score, offer_score)
            out.append(
                ProcurementScore(
                    tenant_id=tenant_id,
                    request_id=request.request_id,
                    quotation_id=q.quotation_id,
                    urgency=urgency_components,
                    urgency_score=urgency_score,
                    offer=offer_components,
                    offer_score=offer_score,
                    decision_band=band,
                    components_json={
                        "ml_p_on_time": pred.p_on_time,
                        "ml_confidence": pred.confidence_band,
                        "anomaly_score": anomaly.anomaly_score if anomaly else None,
                        "anomaly_flagged": anomaly.flagged if anomaly else False,
                        "is_imported": bool(sup and sup.is_importer),
                        "fits_window": q.lead_time_days <= 14,
                    },
                )
            )
        return out


def _extract_payment_days(terms: str | None) -> int | None:
    if not terms:
        return None
    import re

    match = re.search(r"(\d{1,3})\s*(?:dias?|days?)", terms, re.IGNORECASE)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


# Default catalog bands keyed by lowercase substring of the item
# description. These match the calibration in
# ``compras/COMPRAS_AGRO_plan.md`` section 4.3.
_DEFAULT_BANDS: dict[str, CatalogBand] = {
    "urea": CatalogBand("urea", Decimal("380"), Decimal("460")),
    "map": CatalogBand("map", Decimal("620"), Decimal("780")),
    "kcl": CatalogBand("kcl", Decimal("320"), Decimal("420")),
    "glifosato": CatalogBand("glifosato", Decimal("4.20"), Decimal("5.80")),
    "soja semilla": CatalogBand("soja semilla", Decimal("0.95"), Decimal("1.35")),
}
