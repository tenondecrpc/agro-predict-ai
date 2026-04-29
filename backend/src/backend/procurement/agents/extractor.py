"""LLM Agent #1: extractor of structured quotation data from raw text.

Input: free-form text (pasted email, PDF text dump, photo OCR, etc.).
Output: ``ExtractedQuotation`` ready to be confirmed by the buyer.

If the LLM is disabled or fails, a regex-based fallback grabs the
total amount, currency, and lead time so the user still gets a partial
result they can complete manually.
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from decimal import Decimal

from pydantic import ValidationError

from backend.llm.adapter import LLMAdapter
from backend.procurement.agents.base import (
    extract_json,
    is_llm_available,
    safe_complete,
    validate_to_model,
)
from backend.procurement.agents.prompts import EXTRACTOR_PROMPT_TEMPLATE, EXTRACTOR_SYSTEM
from backend.procurement.agents.schemas import ExtractedQuotation
from backend.procurement.models import PurchaseRequest

logger = logging.getLogger(__name__)

_TOTAL_RE = re.compile(
    r"total[^\d]{0,40}([\d\.,]+)",
    re.IGNORECASE,
)
_LEAD_TIME_RE = re.compile(
    r"(\d{1,3})\s*(?:dias?|days?)\s*(?:de\s*)?(?:entrega|delivery|plazo)?",
    re.IGNORECASE,
)
_USD_RE = re.compile(r"(?:USD|US\$|U\$S|d[oó]lar)", re.IGNORECASE)


def _parse_money(raw: str) -> Decimal | None:
    """Tolerant parser for Latin American number formats.

    Handles '1.234.567,89' (es-PY), '1,234,567.89' (en-US), and
    plain '1234567.89'.
    """
    if not raw:
        return None
    cleaned = raw.replace(" ", "").rstrip(".,")
    if cleaned.count(",") and cleaned.count("."):
        # Detect which is the decimal: rightmost separator wins
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(","):
        # Single comma: assume decimal if 1-2 digits follow
        parts = cleaned.split(",")
        if len(parts[-1]) <= 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(".") > 1:
        # Multiple dots, no commas -> es-PY thousand separators (1.234.567)
        cleaned = cleaned.replace(".", "")
    elif cleaned.count(".") == 1:
        # Single dot: decimal if 1-2 digits follow, else thousand sep
        parts = cleaned.split(".")
        if len(parts[-1]) > 2:
            cleaned = cleaned.replace(".", "")
    try:
        return Decimal(cleaned)
    except Exception:  # noqa: BLE001
        return None


def fallback_extract(raw_text: str) -> ExtractedQuotation:
    """Best-effort regex-based extraction. Always returns SOMETHING."""
    total: Decimal | None = None
    match = _TOTAL_RE.search(raw_text)
    if match:
        total = _parse_money(match.group(1))
    if total is None:
        total = Decimal("0")

    lead_time = 14
    lt_match = _LEAD_TIME_RE.search(raw_text)
    if lt_match:
        try:
            candidate = int(lt_match.group(1))
            if 0 <= candidate <= 365:
                lead_time = candidate
        except ValueError:
            pass

    currency = "USD" if _USD_RE.search(raw_text) else "PYG"
    validity = date.today() + timedelta(days=15)

    return ExtractedQuotation(
        currency=currency,  # type: ignore[arg-type]
        total_amount=total,
        lead_time_days=lead_time,
        validity_until_iso=validity,
        items=[],
        extraction_confidence=Decimal("0.30"),
        extraction_source="fallback",
    )


class ExtractorAgent:
    """LLM extractor with deterministic fallback."""

    def __init__(self, llm: LLMAdapter) -> None:
        self._llm = llm

    @property
    def is_llm_enabled(self) -> bool:
        return is_llm_available(self._llm)

    def extract(
        self,
        raw_text: str,
        *,
        request: PurchaseRequest | None = None,
    ) -> ExtractedQuotation:
        if not raw_text or not raw_text.strip():
            return ExtractedQuotation(
                currency="PYG",
                total_amount=Decimal("0"),
                lead_time_days=14,
                validity_until_iso=date.today() + timedelta(days=15),
                extraction_confidence=Decimal("0.0"),
                extraction_source="fallback",
            )

        if not self.is_llm_enabled:
            return fallback_extract(raw_text)

        prompt = EXTRACTOR_PROMPT_TEMPLATE.format(
            request_title=(request.title if request else "(no request context)"),
            request_crop=(request.target_crop or "n/a") if request else "n/a",
            request_items=(
                ", ".join(item.description for item in request.items[:5]) if request else "n/a"
            ),
            raw_text=raw_text.strip(),
        )
        response = safe_complete(self._llm, system=EXTRACTOR_SYSTEM, prompt=prompt)
        if response is None:
            return fallback_extract(raw_text)

        try:
            data = extract_json(response)
            return validate_to_model(data, ExtractedQuotation)
        except (ValueError, ValidationError) as exc:
            logger.warning("extractor LLM output unusable: %s", exc)
            return fallback_extract(raw_text)
