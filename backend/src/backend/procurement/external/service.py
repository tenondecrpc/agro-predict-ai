"""External signals service: cache-aside fetcher for weather and FX.

Both fetchers follow the same pattern:

1. Look up a fresh entry in the cache (``valid_until > now``).
2. If found, return it.
3. Otherwise call the provider, persist the result, return it.
4. On provider failure, return a degraded fallback (FX) or raise (weather).
"""

from __future__ import annotations

import logging

from backend.procurement.external.departments import get_coords
from backend.procurement.external.fx import (
    OpenExchangeRatesClient,
    build_fallback,
    build_rate,
)
from backend.procurement.external.models import FXRate, WeatherSnapshot
from backend.procurement.external.repository import ExternalSignalRepository
from backend.procurement.external.weather import (
    OpenMeteoClient,
    UnknownDepartmentError,
    build_snapshot,
)

logger = logging.getLogger(__name__)


class WeatherService:
    def __init__(
        self,
        repository: ExternalSignalRepository,
        *,
        client: OpenMeteoClient | None = None,
    ) -> None:
        self._repo = repository
        self._client = client or OpenMeteoClient()

    def get_or_fetch(self, *, department: str, horizon_days: int = 10) -> WeatherSnapshot:
        coords = get_coords(department)
        if coords is None:
            raise UnknownDepartmentError(
                f"unknown Paraguayan department: '{department}'. "
                "Expected one of the 17 standard departments plus Asuncion."
            )
        cached = self._repo.get_recent_weather_snapshot(
            department=coords.name, horizon_days=horizon_days
        )
        if cached is not None:
            return cached
        daily = self._client.fetch_daily(coords, horizon_days=horizon_days)
        snapshot = build_snapshot(department, coords, daily, horizon_days=horizon_days)
        return self._repo.save_weather_snapshot(snapshot)


class FXService:
    def __init__(
        self,
        repository: ExternalSignalRepository,
        *,
        client: OpenExchangeRatesClient | None = None,
    ) -> None:
        self._repo = repository
        self._client = client or OpenExchangeRatesClient()

    def get_or_fetch(self, *, base: str = "USD", quote: str = "PYG") -> FXRate:
        cached = self._repo.get_recent_fx_rate(base=base, quote=quote)
        if cached is not None:
            return cached
        try:
            payload = self._client.fetch_pair(base=base, quote=quote)
            from decimal import Decimal

            rate = build_rate(
                rate_reference=Decimal(str(payload["rate_reference"])),
                source=payload["source"],
                base=base,
                quote=quote,
                raw=payload["raw"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("FX provider failed (%s); using fallback rate", exc)
            rate = build_fallback(base=base, quote=quote)
        return self._repo.save_fx_rate(rate)
