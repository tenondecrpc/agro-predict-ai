"""Integration tests for Phase 2 external signals (weather + FX).

All tests use stubbed HTTP clients so no network calls happen in CI.
The Postgres cache repository is exercised by the live backend smoke
check; here we use the in-memory repository.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.procurement.api import build_procurement_router
from backend.procurement.external.fx import OpenExchangeRatesClient, build_rate
from backend.procurement.external.repository import InMemoryExternalSignalRepository
from backend.procurement.external.service import FXService, WeatherService
from backend.procurement.external.weather import (
    OpenMeteoClient,
    compute_components,
    compute_risk_score,
)
from backend.procurement.repository import InMemoryProcurementRepository
from backend.procurement.service import ProcurementService

# ---------------------------------------------------------------------------
# HTTP stubs
# ---------------------------------------------------------------------------


class _StubResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


class _StubHTTPClient:
    """Minimal httpx-like stub. ``responses`` is a dict url->payload."""

    def __init__(self, responses: dict[str, dict] | None = None) -> None:
        self._responses = responses or {}
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, url: str, *, params: dict | None = None, timeout: float | None = None):  # noqa: ANN201
        self.calls.append((url, params))
        if url not in self._responses:
            raise RuntimeError(f"unexpected URL {url}")
        return _StubResponse(self._responses[url])

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _drought_response(days: int = 10) -> dict:
    """Open-Meteo response simulating a drought scenario."""
    return {
        "daily": {
            "precipitation_sum": [0.0] * days,
            "temperature_2m_max": [37.0, 38.5, 36.2, 35.9, 34.8] + [33.0] * (days - 5),
            "temperature_2m_min": [22.0] * days,
            "et0_fao_evapotranspiration": [6.5] * days,
        }
    }


def _favorable_response(days: int = 10) -> dict:
    """Open-Meteo response simulating ample moisture, no heat stress."""
    return {
        "daily": {
            "precipitation_sum": [12.0] * days,
            "temperature_2m_max": [28.0] * days,
            "temperature_2m_min": [18.0] * days,
            "et0_fao_evapotranspiration": [3.5] * days,
        }
    }


def _fx_response(rate: float = 7415.0) -> dict:
    return {
        "result": "success",
        "provider": "open.er-api.com",
        "base_code": "USD",
        "rates": {"PYG": rate, "EUR": 0.92, "ARS": 950.0},
    }


@pytest.fixture
def client_with_drought() -> TestClient:
    proc_repo = InMemoryProcurementRepository()
    ext_repo = InMemoryExternalSignalRepository()
    proc_service = ProcurementService(repository=proc_repo)
    weather_http = _StubHTTPClient({
        "https://api.open-meteo.com/v1/forecast": _drought_response(10),
    })
    fx_http = _StubHTTPClient({
        "https://open.er-api.com/v6/latest/USD": _fx_response(7400.0),
    })
    weather_service = WeatherService(
        repository=ext_repo,
        client=OpenMeteoClient(http_client=weather_http),
    )
    fx_service = FXService(
        repository=ext_repo,
        client=OpenExchangeRatesClient(http_client=fx_http),
    )
    app = FastAPI()
    app.include_router(
        build_procurement_router(
            proc_service,
            weather_service=weather_service,
            fx_service=fx_service,
        )
    )
    return TestClient(app)


# ---------------------------------------------------------------------------
# Pure scoring tests
# ---------------------------------------------------------------------------


def test_drought_scenario_yields_high_score() -> None:
    components = compute_components(_drought_response(10)["daily"])
    score, band, interp = compute_risk_score(components, horizon_days=10)
    assert score >= Decimal("70")
    assert band in ("high", "extreme", "moderate-high")
    assert "drought" in interp


def test_favorable_scenario_yields_low_score() -> None:
    components = compute_components(_favorable_response(10)["daily"])
    score, band, _ = compute_risk_score(components, horizon_days=10)
    assert score <= Decimal("40")
    assert band in ("low", "moderate")


def test_components_count_heat_and_excess_days() -> None:
    daily = {
        "precipitation_sum": [60.0, 5.0, 70.0, 0.0, 0.0],
        "temperature_2m_max": [36.0, 36.5, 33.0, 35.0, 34.9],
        "temperature_2m_min": [22.0, 22.0, 22.0, 22.0, 22.0],
    }
    components = compute_components(daily)
    assert components.excess_rain_days == 2  # >= 50mm on 2 days
    assert components.heat_stress_days == 3  # >= 35C on 3 days


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


def test_unknown_department_raises(client_with_drought: TestClient) -> None:
    response = client_with_drought.get(
        "/api/v1/procurement/weather/risk",
        params={"department": "Atlantis", "horizon_days": 10},
    )
    assert response.status_code == 404


def test_weather_risk_returns_snapshot(client_with_drought: TestClient) -> None:
    response = client_with_drought.get(
        "/api/v1/procurement/weather/risk",
        params={"department": "Itapua", "horizon_days": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["department"] == "Itapua"
    assert body["horizon_days"] == 10
    assert float(body["weather_risk_score"]) >= 70.0
    assert body["risk_band"] in ("high", "extreme", "moderate-high")
    assert body["source"] == "open-meteo"


def test_weather_response_is_cached(client_with_drought: TestClient) -> None:
    r1 = client_with_drought.get(
        "/api/v1/procurement/weather/risk",
        params={"department": "Itapua", "horizon_days": 10},
    ).json()
    r2 = client_with_drought.get(
        "/api/v1/procurement/weather/risk",
        params={"department": "Itapua", "horizon_days": 10},
    ).json()
    # Cache hit: same snapshot_id and same fetched_at on the second call.
    assert r1["snapshot_id"] == r2["snapshot_id"]
    assert r1["fetched_at"] == r2["fetched_at"]


def test_department_normalization_handles_accents(client_with_drought: TestClient) -> None:
    response = client_with_drought.get(
        "/api/v1/procurement/weather/risk",
        params={"department": "Itapúa", "horizon_days": 10},
    )
    assert response.status_code == 200


def test_fx_usd_pyg_returns_rate(client_with_drought: TestClient) -> None:
    response = client_with_drought.get("/api/v1/procurement/fx/usd_pyg")
    assert response.status_code == 200
    body = response.json()
    assert body["base_currency"] == "USD"
    assert body["quote_currency"] == "PYG"
    assert float(body["rate_reference"]) == 7400.0
    assert body["source"] == "open.er-api.com"


def test_fx_falls_back_when_provider_fails() -> None:
    proc_repo = InMemoryProcurementRepository()
    ext_repo = InMemoryExternalSignalRepository()
    proc_service = ProcurementService(repository=proc_repo)

    class _FailingClient:
        def get(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
            raise RuntimeError("simulated provider outage")

        def close(self) -> None:
            pass

    fx_service = FXService(
        repository=ext_repo,
        client=OpenExchangeRatesClient(http_client=_FailingClient()),
    )
    app = FastAPI()
    app.include_router(
        build_procurement_router(
            proc_service,
            weather_service=WeatherService(repository=ext_repo),
            fx_service=fx_service,
        )
    )
    client = TestClient(app)
    response = client.get("/api/v1/procurement/fx/usd_pyg")
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback-fixed"
    assert float(body["rate_reference"]) > 0.0


def test_build_rate_records_validity_window() -> None:
    rate = build_rate(rate_reference=Decimal("7400"), source="test", base="USD", quote="PYG")
    assert rate.valid_until > rate.fetched_at
    assert (rate.valid_until - rate.fetched_at).total_seconds() >= 3500  # ~1 hour
