"""Open-Meteo weather risk fetcher.

Fetches a daily forecast for a Paraguayan department and reduces it
to a composite ``weather_risk_score`` (0-100) used by the procurement
Urgency Score.

The endpoint requires no API key. The MVP keeps the scoring rules in
this module rather than in the database to keep the demo
self-contained and easy to inspect.

Calibration philosophy (driven by ``compras/COMPRAS_AGRO_plan.md``):

- High score (drought, heat stress) means buy now: fertilizer prices
  tend to firm up under drought stress and supply pressure rises.
- Low score (favorable, rain in range) means there is room to wait
  and negotiate.

Bands (composite):

- 0-30   "low"            buy with calm
- 31-50  "moderate"       neutral
- 51-70  "moderate-high"  start negotiating
- 71-85  "high"           close soon
- 86-100 "extreme"        buy now
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

import httpx

from backend.procurement.external.departments import DepartmentCoords
from backend.procurement.external.models import WeatherComponents, WeatherSnapshot

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
ECMWF_URL = "https://api.open-meteo.com/v1/ecmwf"  # Open-Meteo also serves ECMWF model
DEFAULT_TIMEOUT_SECONDS = 5.0
CACHE_TTL_HOURS = 6
HEAT_STRESS_THRESHOLD_C = 35.0
EXCESS_RAIN_THRESHOLD_MM = 50.0

logger = logging.getLogger(__name__)


@runtime_checkable
class HTTPGetter(Protocol):
    """Minimal HTTP surface used by the weather fetcher.

    Tests inject a stub; production uses ``httpx.Client``.
    """

    def get(self, url: str, *, params: dict | None = None, timeout: float | None = None) -> Any: ...


class OpenMeteoClient:
    """Thin wrapper around the Open-Meteo daily forecast endpoint."""

    def __init__(
        self,
        *,
        http_client: HTTPGetter | None = None,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._http = http_client
        self._timeout = timeout_seconds

    def fetch_daily(self, coords: DepartmentCoords, *, horizon_days: int) -> dict[str, Any]:
        params = {
            "latitude": float(coords.lat),
            "longitude": float(coords.lng),
            "daily": ",".join(
                [
                    "precipitation_sum",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "et0_fao_evapotranspiration",
                ]
            ),
            "forecast_days": horizon_days,
            "timezone": "America/Asuncion",
        }
        client: HTTPGetter = self._http or httpx.Client(timeout=self._timeout)
        try:
            response = client.get(OPEN_METEO_URL, params=params, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        finally:
            if self._http is None:
                client.close()  # type: ignore[union-attr]


def _band_for_score(score: Decimal) -> str:
    if score >= 86:
        return "extreme"
    if score >= 71:
        return "high"
    if score >= 51:
        return "moderate-high"
    if score >= 31:
        return "moderate"
    return "low"


def compute_components(daily: dict[str, Any]) -> WeatherComponents:
    """Reduce a daily forecast block to the components we score on."""
    precip_list: list[float] = list(daily.get("precipitation_sum") or [])
    tmax_list: list[float] = list(daily.get("temperature_2m_max") or [])
    tmin_list: list[float] = list(daily.get("temperature_2m_min") or [])

    total_precip = sum(p for p in precip_list if p is not None)
    heat_days = sum(1 for t in tmax_list if t is not None and t >= HEAT_STRESS_THRESHOLD_C)
    excess_days = sum(1 for p in precip_list if p is not None and p >= EXCESS_RAIN_THRESHOLD_MM)
    max_t = max((t for t in tmax_list if t is not None), default=None)
    min_t = min((t for t in tmin_list if t is not None), default=None)

    return WeatherComponents(
        precipitation_sum_mm=Decimal(str(round(total_precip, 2))),
        heat_stress_days=heat_days,
        excess_rain_days=excess_days,
        max_temp_c=Decimal(str(round(max_t, 2))) if max_t is not None else None,
        min_temp_c=Decimal(str(round(min_t, 2))) if min_t is not None else None,
    )


def compute_risk_score(components: WeatherComponents, *, horizon_days: int) -> tuple[Decimal, str, str]:
    """Return (score, band, human-readable interpretation).

    Scoring is a deterministic weighted heuristic. The plan calls out
    that an ``era5`` historical baseline would refine the precipitation
    anomaly calculation; the MVP uses absolute thresholds calibrated for
    a 7-10 day horizon over Paraguayan agro regions.
    """

    precip = float(components.precipitation_sum_mm or 0)
    heat_days = components.heat_stress_days or 0
    excess_days = components.excess_rain_days or 0

    # Drought signal: scale total precipitation deficit relative to a
    # season-typical 80mm over 10 days. Lower precip -> higher drought.
    expected_precip = max(horizon_days * 8.0, 1.0)  # mm
    deficit_ratio = max(0.0, (expected_precip - precip) / expected_precip)
    drought_component = min(100.0, deficit_ratio * 100.0)

    # Heat stress: 0 days -> 0, 5+ days -> 100 (linear)
    heat_component = min(100.0, (heat_days / 5.0) * 100.0)

    # Excess rain depresses urgency a bit (dampens drought) but raises
    # logistics risk. Treat it as a moderate floor.
    excess_component = min(60.0, excess_days * 30.0)

    # Composite weights tuned for procurement urgency (drought drives prices)
    score_float = 0.55 * drought_component + 0.30 * heat_component + 0.15 * excess_component
    score = Decimal(str(round(score_float, 2)))
    band = _band_for_score(score)

    interp_parts: list[str] = []
    if drought_component >= 70:
        interp_parts.append(f"drought signal: only {precip:.1f}mm forecast over {horizon_days}d")
    elif drought_component <= 20:
        interp_parts.append(f"adequate moisture: {precip:.1f}mm forecast")
    if heat_days >= 3:
        interp_parts.append(f"heat stress on {heat_days} days")
    if excess_days >= 2:
        interp_parts.append(f"heavy rain on {excess_days} days (logistics risk)")
    interpretation = "; ".join(interp_parts) or "neutral conditions"

    return score, band, interpretation


def build_snapshot(
    department: str,
    coords: DepartmentCoords,
    daily: dict[str, Any],
    *,
    horizon_days: int,
    source: str = "open-meteo",
) -> WeatherSnapshot:
    components = compute_components(daily.get("daily") or {})
    score, band, interpretation = compute_risk_score(components, horizon_days=horizon_days)
    now = datetime.now(UTC)
    return WeatherSnapshot(
        department=coords.name,
        geo_lat=coords.lat,
        geo_lng=coords.lng,
        horizon_days=horizon_days,
        fetched_at=now,
        valid_until=now + timedelta(hours=CACHE_TTL_HOURS),
        components=components,
        weather_risk_score=score,
        risk_band=band,  # type: ignore[arg-type]
        interpretation=interpretation,
        raw_response=daily,
        source=source,
    )


class UnknownDepartmentError(LookupError):
    pass
