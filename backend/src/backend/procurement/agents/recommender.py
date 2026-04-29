"""LLM Agent #3: recommender that produces a justified Markdown decision.

The LLM does NOT compute scores - they come from the deterministic
scoring layer (``backend.procurement.scoring``). The agent's job is
to articulate a Markdown narrative grounded in those numbers, citing
evidence from the comparison, ML predictions, and anomaly flags.

Fallback: a templated Markdown that fills in the same fields without
LLM polish.
"""

from __future__ import annotations

import json
import logging
from decimal import Decimal

from backend.llm.adapter import LLMAdapter
from backend.procurement.agents.base import is_llm_available, safe_complete
from backend.procurement.agents.prompts import RECOMMENDER_PROMPT_TEMPLATE, RECOMMENDER_SYSTEM
from backend.procurement.agents.schemas import ComparisonResult, Recommendation
from backend.procurement.ml.models import AnomalyResult, SupplierPrediction
from backend.procurement.models import PurchaseRequest, Quotation, Supplier
from backend.procurement.scoring.models import ProcurementScore

logger = logging.getLogger(__name__)


def _build_fallback_markdown(
    *,
    request: PurchaseRequest,
    recommended_score: ProcurementScore,
    recommended_quotation: Quotation,
    recommended_supplier: Supplier | None,
    other_scores: list[ProcurementScore],
    other_quotations_by_id: dict[str, Quotation],
    other_suppliers_by_id: dict[str, Supplier],
    ml_predictions: dict[str, SupplierPrediction],
    anomalies: dict[str, AnomalyResult],
) -> str:
    weights = request.criteria_weights
    sup_name = recommended_supplier.legal_name if recommended_supplier else recommended_quotation.supplier_id
    composite = (recommended_score.urgency_score + recommended_score.offer_score) / Decimal("2")

    lines: list[str] = []
    lines.append(f"## Recommendation: {sup_name} - {request.title}")
    lines.append("")
    lines.append(
        f"**Composite score:** {composite:.2f}/100 - **{recommended_score.decision_band}**"
    )
    lines.append("")
    lines.append("### Justification")
    lines.append(
        f"Urgency score {recommended_score.urgency_score} (weather risk "
        f"{recommended_score.urgency.weather_risk}, delivery urgency "
        f"{recommended_score.urgency.delivery_urgency}, market volatility "
        f"{recommended_score.urgency.market_volatility}) combined with offer "
        f"score {recommended_score.offer_score} place this quotation in band "
        f"'{recommended_score.decision_band}' per the deterministic decision matrix."
    )
    lines.append("")
    lines.append("### Scoring breakdown")
    lines.append(
        f"- **Price (weight {weights.price}%):** total {recommended_quotation.total_amount} "
        f"{recommended_quotation.currency}, lead time {recommended_quotation.lead_time_days} days."
    )
    pred = ml_predictions.get(recommended_quotation.supplier_id)
    if pred is not None:
        lines.append(
            f"- **Delivery (weight {weights.delivery}%):** ML predicts "
            f"{pred.p_on_time:.0%} probability of on-time delivery "
            f"(based on {pred.based_on_n_observations} prior observations, "
            f"confidence: {pred.confidence_band})."
        )
    else:
        lines.append(
            f"- **Delivery (weight {weights.delivery}%):** no ML prediction available."
        )
    if recommended_quotation.warranty_months:
        lines.append(
            f"- **Quality (weight {weights.quality}%):** warranty "
            f"{recommended_quotation.warranty_months} months."
        )
    if recommended_quotation.payment_terms:
        lines.append(
            f"- **Commercial terms (weight {weights.terms}%):** "
            f"{recommended_quotation.payment_terms}."
        )
    lines.append("")

    if other_scores:
        lines.append("### Alternatives considered")
        for score in sorted(other_scores, key=lambda s: -s.offer_score)[:3]:
            other_q = other_quotations_by_id.get(score.quotation_id)
            other_s = other_suppliers_by_id.get(other_q.supplier_id) if other_q else None
            name = other_s.legal_name if other_s else (other_q.supplier_id if other_q else "?")
            other_pred = ml_predictions.get(other_q.supplier_id) if other_q else None
            line = (
                f"- {name}: offer score {score.offer_score}, "
                f"decision '{score.decision_band}'"
            )
            if other_pred is not None:
                line += f", ML p_on_time {other_pred.p_on_time:.0%}"
            lines.append(line)
        lines.append("")

    risky_anomalies = [a for a in anomalies.values() if a.flagged]
    if risky_anomalies:
        lines.append("### Risks identified")
        for a in risky_anomalies:
            lines.append(f"- Quotation {a.quotation_id}: {a.reason}")
        lines.append("")
    else:
        lines.append("### Risks identified")
        lines.append("No material risks identified.")
        lines.append("")

    lines.append("### Suggested action")
    if recommended_score.decision_band == "buy_now":
        lines.append("Proceed with award. Conditions are aligned for immediate purchase.")
    elif recommended_score.decision_band == "negotiate_and_close":
        lines.append("Use the Negotiator agent to request the gaps before awarding.")
    elif recommended_score.decision_band == "buy_with_followup":
        lines.append("Proceed with award and monitor delivery progress weekly.")
    elif recommended_score.decision_band == "wait_better_offer":
        lines.append("Hold the award and request better terms from existing or new suppliers.")
    else:
        lines.append("Do not award. Re-quote with revised specifications.")

    return "\n".join(lines)


def _summarize_for_prompt(items: dict[str, object]) -> str:
    return json.dumps(items, default=str)


class RecommenderAgent:
    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    def recommend(
        self,
        *,
        request: PurchaseRequest,
        comparison: ComparisonResult,
        scores: list[ProcurementScore],
        quotations_by_id: dict[str, Quotation],
        suppliers_by_id: dict[str, Supplier],
        ml_predictions: dict[str, SupplierPrediction],
        anomalies: dict[str, AnomalyResult],
    ) -> Recommendation:
        if not scores:
            raise ValueError("at least one score is required to recommend")

        # Pick the highest combined score whose offer is acceptable
        eligible = [s for s in scores if s.decision_band != "not_recommended"]
        candidates = eligible or scores
        best = max(candidates, key=lambda s: (s.urgency_score + s.offer_score))
        composite = (best.urgency_score + best.offer_score) / Decimal("2")
        recommended_quotation = quotations_by_id[best.quotation_id]
        recommended_supplier = suppliers_by_id.get(recommended_quotation.supplier_id)
        others = [s for s in scores if s.quotation_id != best.quotation_id]

        fallback_md = _build_fallback_markdown(
            request=request,
            recommended_score=best,
            recommended_quotation=recommended_quotation,
            recommended_supplier=recommended_supplier,
            other_scores=others,
            other_quotations_by_id=quotations_by_id,
            other_suppliers_by_id=suppliers_by_id,
            ml_predictions=ml_predictions,
            anomalies=anomalies,
        )

        if not is_llm_available(self._llm):
            return Recommendation(
                recommended_quotation_id=best.quotation_id,
                recommended_supplier_id=recommended_quotation.supplier_id,
                decision_band=best.decision_band,
                composite_score=composite.quantize(Decimal("0.01")),
                urgency_score=best.urgency_score,
                offer_score=best.offer_score,
                reasoning_markdown=fallback_md,
                source="fallback",
            )

        prompt = RECOMMENDER_PROMPT_TEMPLATE.format(
            request_summary=_summarize_for_prompt(
                {
                    "request_id": request.request_id,
                    "title": request.title,
                    "target_crop": request.target_crop,
                    "fenological_window": request.fenological_window,
                    "criteria_weights": request.criteria_weights.model_dump(),
                }
            ),
            comparison_json=_summarize_for_prompt(comparison.model_dump()),
            ml_predictions_json=_summarize_for_prompt(
                {sid: pred.model_dump() for sid, pred in ml_predictions.items()}
            ),
            anomalies_json=_summarize_for_prompt(
                {qid: a.model_dump() for qid, a in anomalies.items()}
            ),
            scores_json=_summarize_for_prompt([s.model_dump() for s in scores]),
            weights_json=_summarize_for_prompt(request.criteria_weights.model_dump()),
            recommended_quotation_id=best.quotation_id,
            weight_price=request.criteria_weights.price,
            weight_delivery=request.criteria_weights.delivery,
            weight_quality=request.criteria_weights.quality,
            weight_terms=request.criteria_weights.terms,
        )
        response = safe_complete(self._llm, system=RECOMMENDER_SYSTEM, prompt=prompt)
        markdown = response.strip() if response else fallback_md
        source = "llm" if response else "fallback"

        return Recommendation(
            recommended_quotation_id=best.quotation_id,
            recommended_supplier_id=recommended_quotation.supplier_id,
            decision_band=best.decision_band,
            composite_score=composite.quantize(Decimal("0.01")),
            urgency_score=best.urgency_score,
            offer_score=best.offer_score,
            reasoning_markdown=markdown,
            source=source,  # type: ignore[arg-type]
        )
