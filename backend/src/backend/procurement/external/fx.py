"""USD to PYG (and other pairs) exchange rate fetcher.

Tries a free public source (open.er-api.com) and falls back to a
configurable fixed reference rate. The cached value is good enough for
hackathon-grade procurement comparisons; production deployments would
swap in a BCP feed.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx

from backend.procurement.external.models import FXRate

OPEN_ER_API_URL = "https://open.er-api.com/v6/latest"
DEFAULT_TIMEOUT_SECONDS = 5.0
CACHE_TTL_HOURS = 1
FALLBACK_RATE_ENV = "BACKEND_FX_USD_PYG_FALLBACK"
DEFAULT_FALLBACK_RATE = Decimal("7400.00")

logger = logging.getLogger(__name__)


class OpenExchangeRatesClient:
    """Calls https://open.er-api.com/v6/latest/<base>.

    Free, no key, returns a JSON map of rates against the base currency.
    Reasonable for a hackathon; not for production.
    """

    def __init__(
        self,
        *,
        http_client: Any | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._http = http_client
        self._timeout = timeout_seconds

    def fetch_pair(self, base: str = "USD", quote: str = "PYG") -> dict[str, Any]:
        url = f"{OPEN_ER_API_URL}/{base}"
        client = self._http or httpx.Client(timeout=self._timeout)
        try:
            response = client.get(url, timeout=self._timeout)
            response.raise_for_status()
            payload = response.json()
        finally:
            if self._http is None:
                client.close()
        if payload.get("result") != "success":
            raise RuntimeError(f"FX provider returned non-success result: {payload.get('result')}")
        rates = payload.get("rates") or {}
        if quote not in rates:
            raise RuntimeError(f"FX provider does not include {quote} in {base} rates")
        return {
            "rate_reference": rates[quote],
            "raw": payload,
            "source": payload.get("provider", "open.er-api.com"),
        }


def fallback_rate() -> Decimal:
    raw = os.environ.get(FALLBACK_RATE_ENV)
    if raw is None:
        return DEFAULT_FALLBACK_RATE
    try:
        return Decimal(raw)
    except (ValueError, TypeError):
        logger.warning("invalid %s value %r; using default", FALLBACK_RATE_ENV, raw)
        return DEFAULT_FALLBACK_RATE


def build_rate(
    *,
    rate_reference: Decimal,
    source: str,
    base: str = "USD",
    quote: str = "PYG",
    raw: dict | None = None,
) -> FXRate:
    now = datetime.now(UTC)
    return FXRate(
        base_currency=base,
        quote_currency=quote,
        rate_reference=rate_reference,
        source=source,
        fetched_at=now,
        valid_until=now + timedelta(hours=CACHE_TTL_HOURS),
        raw_response=raw or {},
    )


def build_fallback(*, base: str = "USD", quote: str = "PYG") -> FXRate:
    return build_rate(
        rate_reference=fallback_rate(),
        source="fallback-fixed",
        base=base,
        quote=quote,
        raw={"reason": "external FX provider unavailable"},
    )
