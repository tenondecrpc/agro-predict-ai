"""LLM Agent #4: negotiation message generator.

Output: a Spanish-language email body to send to the supplier asking
for the requested improvements. Tone is cordial, formal, with the
typical Paraguayan agro cooperative-supplier rapport.

Fallback: a templated Spanish email built from the same inputs.
"""

from __future__ import annotations

import json
import logging
from typing import Literal

from backend.llm.adapter import LLMAdapter
from backend.procurement.agents.base import is_llm_available, safe_complete
from backend.procurement.agents.prompts import NEGOTIATOR_PROMPT_TEMPLATE, NEGOTIATOR_SYSTEM
from backend.procurement.agents.schemas import NegotiationMessage
from backend.procurement.models import PurchaseRequest, Quotation, Supplier

logger = logging.getLogger(__name__)

Tone = Literal["cordial", "formal", "asertivo"]


def _summarize_quotation(quotation: Quotation, supplier: Supplier | None) -> str:
    return json.dumps(
        {
            "supplier_legal_name": supplier.legal_name if supplier else quotation.supplier_id,
            "currency": quotation.currency,
            "total_amount": str(quotation.total_amount),
            "lead_time_days": quotation.lead_time_days,
            "warranty_months": quotation.warranty_months,
            "payment_terms": quotation.payment_terms,
        },
        default=str,
    )


def _summarize_alternative(alt: Quotation | None) -> str:
    if alt is None:
        return json.dumps({"available": False})
    return json.dumps(
        {
            "available": True,
            "currency": alt.currency,
            "total_amount": str(alt.total_amount),
            "lead_time_days": alt.lead_time_days,
            "warranty_months": alt.warranty_months,
        },
        default=str,
    )


def _fallback_message(
    *,
    quotation: Quotation,
    supplier: Supplier | None,
    request: PurchaseRequest,
    target_improvements: dict,
    tone: Tone,
) -> str:
    sup_name = supplier.legal_name if supplier else quotation.supplier_id
    target_price_pct = target_improvements.get("price_pct")
    target_lead = target_improvements.get("lead_time_days")
    crop = request.target_crop or "el cultivo"
    window = request.fenological_window or "la ventana de aplicacion"
    asks: list[str] = []
    if target_price_pct is not None:
        asks.append(
            f"Hemos recibido propuestas alternativas competitivas que se "
            f"posicionan aproximadamente {abs(target_price_pct)}% por debajo "
            "de su cotizacion. Solicitamos evaluar un ajuste de precio que "
            "nos permita acercarnos a esas condiciones de mercado."
        )
    if target_lead is not None:
        asks.append(
            f"La ventana fenologica de {window} para el cultivo de {crop} "
            f"requiere disponibilidad del producto en {target_lead} dias "
            "desde la firma de la orden. Quedamos a la espera de su "
            "confirmacion sobre la viabilidad logistica."
        )
    if not asks:
        asks.append(
            "Quedamos a la espera de su mejor propuesta para avanzar con la "
            "adjudicacion."
        )

    body = (
        f"Estimado equipo comercial de {sup_name},\n\n"
        "Reciban un cordial saludo desde nuestra cooperativa. Agradecemos "
        f"la cotizacion recibida para el suministro asociado a la solicitud "
        f"\"{request.title}\". Su propuesta es competitiva y valoramos "
        f"especialmente el plazo de entrega de {quotation.lead_time_days} dias.\n\n"
        + "\n\n".join(f"{i + 1}. {ask}" for i, ask in enumerate(asks))
        + "\n\nQuedamos a su disposicion para coordinar los siguientes pasos. "
        "Agradecemos la rapidez en este proceso ya que la decision de "
        "adjudicacion se tomara esta semana.\n\n"
        "Saludos cordiales,\n"
        "[Nombre del Gerente de Compras]\n"
        "[Cooperativa]"
    )
    return body


class NegotiatorAgent:
    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    def draft(
        self,
        *,
        quotation: Quotation,
        supplier: Supplier | None,
        request: PurchaseRequest,
        best_alternative: Quotation | None,
        target_improvements: dict,
        tone: Tone = "cordial",
    ) -> NegotiationMessage:
        if not is_llm_available(self._llm):
            return NegotiationMessage(
                message_text=_fallback_message(
                    quotation=quotation,
                    supplier=supplier,
                    request=request,
                    target_improvements=target_improvements,
                    tone=tone,
                ),
                tone=tone,
                target_improvements=target_improvements,
                source="fallback",
            )

        prompt = NEGOTIATOR_PROMPT_TEMPLATE.format(
            quotation_summary=_summarize_quotation(quotation, supplier),
            best_alternative_summary=_summarize_alternative(best_alternative),
            target_improvements=json.dumps(target_improvements, default=str),
            tone=tone,
            target_crop=request.target_crop or "n/a",
            fenological_window=request.fenological_window or "n/a",
        )
        response = safe_complete(self._llm, system=NEGOTIATOR_SYSTEM, prompt=prompt)
        if response is None or not response.strip():
            return NegotiationMessage(
                message_text=_fallback_message(
                    quotation=quotation,
                    supplier=supplier,
                    request=request,
                    target_improvements=target_improvements,
                    tone=tone,
                ),
                tone=tone,
                target_improvements=target_improvements,
                source="fallback",
            )

        return NegotiationMessage(
            message_text=response.strip(),
            tone=tone,
            target_improvements=target_improvements,
            source="llm",
        )
