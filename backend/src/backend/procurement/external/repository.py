"""Cache repository for weather snapshots and FX rates.

Two implementations: in-memory (tests, air-gapped) and Postgres
(production). Both honor the ``valid_until`` field to expire stale
entries.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import Engine, create_engine, text

from backend.procurement.external.models import FXRate, WeatherSnapshot


@runtime_checkable
class ExternalSignalRepository(Protocol):
    def save_weather_snapshot(self, snapshot: WeatherSnapshot) -> WeatherSnapshot: ...
    def get_recent_weather_snapshot(
        self, *, department: str, horizon_days: int
    ) -> WeatherSnapshot | None: ...
    def save_fx_rate(self, rate: FXRate) -> FXRate: ...
    def get_recent_fx_rate(self, *, base: str, quote: str) -> FXRate | None: ...


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------


class InMemoryExternalSignalRepository:
    def __init__(self) -> None:
        self._weather: list[WeatherSnapshot] = []
        self._fx: list[FXRate] = []

    def save_weather_snapshot(self, snapshot: WeatherSnapshot) -> WeatherSnapshot:
        self._weather.append(snapshot.model_copy(deep=True))
        return snapshot

    def get_recent_weather_snapshot(
        self, *, department: str, horizon_days: int
    ) -> WeatherSnapshot | None:
        from backend.procurement.external.departments import normalize

        target = normalize(department)
        candidates = [
            s
            for s in self._weather
            if normalize(s.department) == target
            and s.horizon_days == horizon_days
            and s.valid_until > _now()
        ]
        if not candidates:
            return None
        latest = max(candidates, key=lambda s: s.fetched_at)
        return latest.model_copy(deep=True)

    def save_fx_rate(self, rate: FXRate) -> FXRate:
        self._fx.append(rate.model_copy(deep=True))
        return rate

    def get_recent_fx_rate(self, *, base: str, quote: str) -> FXRate | None:
        candidates = [
            r
            for r in self._fx
            if r.base_currency == base and r.quote_currency == quote and r.valid_until > _now()
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda r: r.fetched_at).model_copy(deep=True)


# ---------------------------------------------------------------------------
# Postgres implementation
# ---------------------------------------------------------------------------


class PostgresExternalSignalRepository:
    def __init__(
        self,
        database_url: str,
        *,
        engine: Engine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._engine = engine or create_engine(database_url, future=True, pool_pre_ping=True)
        self._logger = logger or logging.getLogger(__name__)

    def save_weather_snapshot(self, snapshot: WeatherSnapshot) -> WeatherSnapshot:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_weather_snapshots (
                        snapshot_id, department, geo_lat, geo_lng, horizon_days,
                        fetched_at, valid_until, precipitation_sum_mm, heat_stress_days,
                        excess_rain_days, max_temp_c, min_temp_c, weather_risk_score,
                        risk_band, interpretation, raw_response, source
                    ) VALUES (
                        :snapshot_id, :department, :geo_lat, :geo_lng, :horizon_days,
                        :fetched_at, :valid_until, :precipitation_sum_mm, :heat_stress_days,
                        :excess_rain_days, :max_temp_c, :min_temp_c, :weather_risk_score,
                        :risk_band, :interpretation, CAST(:raw_response AS JSONB), :source
                    )
                    """
                ),
                {
                    "snapshot_id": snapshot.snapshot_id,
                    "department": snapshot.department,
                    "geo_lat": snapshot.geo_lat,
                    "geo_lng": snapshot.geo_lng,
                    "horizon_days": snapshot.horizon_days,
                    "fetched_at": snapshot.fetched_at,
                    "valid_until": snapshot.valid_until,
                    "precipitation_sum_mm": snapshot.components.precipitation_sum_mm,
                    "heat_stress_days": snapshot.components.heat_stress_days,
                    "excess_rain_days": snapshot.components.excess_rain_days,
                    "max_temp_c": snapshot.components.max_temp_c,
                    "min_temp_c": snapshot.components.min_temp_c,
                    "weather_risk_score": snapshot.weather_risk_score,
                    "risk_band": snapshot.risk_band,
                    "interpretation": snapshot.interpretation,
                    "raw_response": _json_dumps(snapshot.raw_response),
                    "source": snapshot.source,
                },
            )
        return snapshot

    def get_recent_weather_snapshot(
        self, *, department: str, horizon_days: int
    ) -> WeatherSnapshot | None:
        from backend.procurement.external.departments import normalize

        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT snapshot_id, department, geo_lat, geo_lng, horizon_days,
                               fetched_at, valid_until, precipitation_sum_mm,
                               heat_stress_days, excess_rain_days, max_temp_c, min_temp_c,
                               weather_risk_score, risk_band, interpretation,
                               raw_response, source
                        FROM procurement_weather_snapshots
                        WHERE LOWER(department) = LOWER(:department)
                          AND horizon_days = :horizon_days
                          AND valid_until > now()
                        ORDER BY fetched_at DESC
                        LIMIT 1
                        """
                    ),
                    {"department": normalize(department).title(), "horizon_days": horizon_days},
                )
                .mappings()
                .fetchone()
            )
        if row is None:
            return None
        from backend.procurement.external.models import WeatherComponents

        return WeatherSnapshot(
            snapshot_id=row["snapshot_id"],
            department=row["department"],
            geo_lat=row["geo_lat"],
            geo_lng=row["geo_lng"],
            horizon_days=row["horizon_days"],
            fetched_at=row["fetched_at"],
            valid_until=row["valid_until"],
            components=WeatherComponents(
                precipitation_sum_mm=row["precipitation_sum_mm"],
                heat_stress_days=row["heat_stress_days"],
                excess_rain_days=row["excess_rain_days"],
                max_temp_c=row["max_temp_c"],
                min_temp_c=row["min_temp_c"],
            ),
            weather_risk_score=row["weather_risk_score"],
            risk_band=row["risk_band"],
            interpretation=row["interpretation"],
            raw_response=row["raw_response"] or {},
            source=row["source"],
        )

    def save_fx_rate(self, rate: FXRate) -> FXRate:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_fx_rates (
                        rate_id, base_currency, quote_currency, rate_buy, rate_sell,
                        rate_reference, source, fetched_at, valid_until, raw_response
                    ) VALUES (
                        :rate_id, :base_currency, :quote_currency, :rate_buy, :rate_sell,
                        :rate_reference, :source, :fetched_at, :valid_until,
                        CAST(:raw_response AS JSONB)
                    )
                    """
                ),
                {
                    "rate_id": rate.rate_id,
                    "base_currency": rate.base_currency,
                    "quote_currency": rate.quote_currency,
                    "rate_buy": rate.rate_buy,
                    "rate_sell": rate.rate_sell,
                    "rate_reference": rate.rate_reference,
                    "source": rate.source,
                    "fetched_at": rate.fetched_at,
                    "valid_until": rate.valid_until,
                    "raw_response": _json_dumps(rate.raw_response),
                },
            )
        return rate

    def get_recent_fx_rate(self, *, base: str, quote: str) -> FXRate | None:
        with self._engine.connect() as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT rate_id, base_currency, quote_currency, rate_buy, rate_sell,
                               rate_reference, source, fetched_at, valid_until, raw_response
                        FROM procurement_fx_rates
                        WHERE base_currency = :base AND quote_currency = :quote
                          AND valid_until > now()
                        ORDER BY fetched_at DESC
                        LIMIT 1
                        """
                    ),
                    {"base": base, "quote": quote},
                )
                .mappings()
                .fetchone()
            )
        if row is None:
            return None
        return FXRate(
            rate_id=row["rate_id"],
            base_currency=row["base_currency"],
            quote_currency=row["quote_currency"],
            rate_buy=row["rate_buy"],
            rate_sell=row["rate_sell"],
            rate_reference=row["rate_reference"],
            source=row["source"],
            fetched_at=row["fetched_at"],
            valid_until=row["valid_until"],
            raw_response=row["raw_response"] or {},
        )
