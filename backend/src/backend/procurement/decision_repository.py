"""Persistence for procurement decisions: scores, recommendations, negotiation messages.

Separated from ``procurement.repository`` (which handles the domain
entities: requests, suppliers, quotations) so the orchestration layer
has a clean, focused dependency.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import Connection, Engine, create_engine, text

from backend.persistence.db import tenant_guc_values
from backend.procurement.agents.schemas import NegotiationMessage, Recommendation
from backend.procurement.ml.models import SupplierPerformanceRecord
from backend.procurement.scoring.models import ProcurementScore


@runtime_checkable
class DecisionRepository(Protocol):
    def save_score(self, score: ProcurementScore) -> ProcurementScore: ...
    def list_scores_for_request(
        self, request_id: str, *, tenant_id: str
    ) -> list[ProcurementScore]: ...
    def save_recommendation(
        self,
        recommendation: Recommendation,
        *,
        tenant_id: str,
        request_id: str,
        recommendation_id: str | None = None,
    ) -> str: ...
    def get_latest_recommendation(
        self, request_id: str, *, tenant_id: str
    ) -> dict | None: ...
    def save_negotiation_message(
        self,
        message: NegotiationMessage,
        *,
        tenant_id: str,
        request_id: str,
        quotation_id: str,
        supplier_id: str,
        message_id: str | None = None,
    ) -> str: ...

    # Supplier performance history (used by the ML predictor)
    def save_history_records(
        self, records: list[SupplierPerformanceRecord]
    ) -> int: ...
    def list_history_for_supplier(
        self, supplier_id: str, *, tenant_id: str | None = None, limit: int = 200
    ) -> list[SupplierPerformanceRecord]: ...


# ---------------------------------------------------------------------------
# In-memory implementation (tests and air-gapped fallback)
# ---------------------------------------------------------------------------


class InMemoryDecisionRepository:
    def __init__(self) -> None:
        self._scores: list[ProcurementScore] = []
        self._recommendations: list[dict] = []
        self._messages: list[dict] = []
        self._history: list[SupplierPerformanceRecord] = []

    def save_score(self, score: ProcurementScore) -> ProcurementScore:
        self._scores.append(score.model_copy(deep=True))
        return score

    def list_scores_for_request(
        self, request_id: str, *, tenant_id: str
    ) -> list[ProcurementScore]:
        return [
            s.model_copy(deep=True)
            for s in self._scores
            if s.tenant_id == tenant_id and s.request_id == request_id
        ]

    def save_recommendation(
        self,
        recommendation: Recommendation,
        *,
        tenant_id: str,
        request_id: str,
        recommendation_id: str | None = None,
    ) -> str:
        from uuid import uuid4

        rid = recommendation_id or str(uuid4())
        record = {
            "recommendation_id": rid,
            "tenant_id": tenant_id,
            "request_id": request_id,
            **recommendation.model_dump(),
        }
        self._recommendations.append(record)
        return rid

    def get_latest_recommendation(
        self, request_id: str, *, tenant_id: str
    ) -> dict | None:
        matching = [
            r
            for r in self._recommendations
            if r["tenant_id"] == tenant_id and r["request_id"] == request_id
        ]
        return matching[-1] if matching else None

    def save_negotiation_message(
        self,
        message: NegotiationMessage,
        *,
        tenant_id: str,
        request_id: str,
        quotation_id: str,
        supplier_id: str,
        message_id: str | None = None,
    ) -> str:
        from uuid import uuid4

        mid = message_id or str(uuid4())
        record = {
            "message_id": mid,
            "tenant_id": tenant_id,
            "request_id": request_id,
            "quotation_id": quotation_id,
            "supplier_id": supplier_id,
            **message.model_dump(),
        }
        self._messages.append(record)
        return mid

    def save_history_records(
        self, records: list[SupplierPerformanceRecord]
    ) -> int:
        for r in records:
            self._history.append(r.model_copy(deep=True))
        return len(records)

    def list_history_for_supplier(
        self, supplier_id: str, *, tenant_id: str | None = None, limit: int = 200
    ) -> list[SupplierPerformanceRecord]:
        out = [
            r
            for r in self._history
            if r.supplier_id == supplier_id
            and (tenant_id is None or r.tenant_id == tenant_id)
        ]
        out.sort(key=lambda r: r.awarded_date, reverse=True)
        return [r.model_copy(deep=True) for r in out[:limit]]


# ---------------------------------------------------------------------------
# Postgres implementation
# ---------------------------------------------------------------------------


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


class PostgresDecisionRepository:
    def __init__(
        self,
        database_url: str,
        *,
        engine: Engine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._engine = engine or create_engine(database_url, future=True, pool_pre_ping=True)
        self._logger = logger or logging.getLogger(__name__)

    @contextmanager
    def _scoped_transaction(self, tenant_id: str) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            for key, value in tenant_guc_values(tenant_id=tenant_id, team_id="*").items():
                connection.execute(
                    text("SELECT set_config(:key, :value, true)"),
                    {"key": key, "value": value},
                )
            yield connection

    @contextmanager
    def _scoped_connection(self, tenant_id: str) -> Iterator[Connection]:
        with self._engine.connect() as connection:
            for key, value in tenant_guc_values(tenant_id=tenant_id, team_id="*").items():
                connection.execute(
                    text("SELECT set_config(:key, :value, true)"),
                    {"key": key, "value": value},
                )
            yield connection

    # Scores ------------------------------------------------------------
    def save_score(self, score: ProcurementScore) -> ProcurementScore:
        with self._scoped_transaction(score.tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_scores (
                        score_id, tenant_id, request_id, quotation_id,
                        weather_risk, delivery_urgency, market_volatility, urgency_score,
                        supplier_score, commercial_terms_score, delivery_risk, offer_score,
                        decision_band, components_json
                    ) VALUES (
                        :score_id, :tenant_id, :request_id, :quotation_id,
                        :weather_risk, :delivery_urgency, :market_volatility, :urgency_score,
                        :supplier_score, :commercial_terms_score, :delivery_risk, :offer_score,
                        :decision_band, CAST(:components_json AS JSONB)
                    )
                    """
                ),
                {
                    "score_id": score.score_id,
                    "tenant_id": score.tenant_id,
                    "request_id": score.request_id,
                    "quotation_id": score.quotation_id,
                    "weather_risk": score.urgency.weather_risk,
                    "delivery_urgency": score.urgency.delivery_urgency,
                    "market_volatility": score.urgency.market_volatility,
                    "urgency_score": score.urgency_score,
                    "supplier_score": score.offer.supplier_score,
                    "commercial_terms_score": score.offer.commercial_terms_score,
                    "delivery_risk": score.offer.delivery_risk,
                    "offer_score": score.offer_score,
                    "decision_band": score.decision_band,
                    "components_json": _json_dumps(score.components_json),
                },
            )
        return score

    def list_scores_for_request(
        self, request_id: str, *, tenant_id: str
    ) -> list[ProcurementScore]:
        from backend.procurement.scoring.models import OfferComponents, UrgencyComponents

        with self._scoped_connection(tenant_id) as conn:
            rows = (
                conn.execute(
                    text(
                        """
                        SELECT score_id, tenant_id, request_id, quotation_id,
                               weather_risk, delivery_urgency, market_volatility,
                               urgency_score, supplier_score, commercial_terms_score,
                               delivery_risk, offer_score, decision_band,
                               components_json, computed_at
                        FROM procurement_scores
                        WHERE tenant_id = :tenant_id AND request_id = :request_id
                        ORDER BY computed_at DESC
                        """
                    ),
                    {"tenant_id": tenant_id, "request_id": request_id},
                )
                .mappings()
                .fetchall()
            )
        return [
            ProcurementScore(
                score_id=r["score_id"],
                tenant_id=r["tenant_id"],
                request_id=r["request_id"],
                quotation_id=r["quotation_id"],
                urgency=UrgencyComponents(
                    weather_risk=r["weather_risk"],
                    delivery_urgency=r["delivery_urgency"],
                    market_volatility=r["market_volatility"],
                ),
                urgency_score=r["urgency_score"],
                offer=OfferComponents(
                    supplier_score=r["supplier_score"],
                    commercial_terms_score=r["commercial_terms_score"],
                    delivery_risk=r["delivery_risk"],
                ),
                offer_score=r["offer_score"],
                decision_band=r["decision_band"],
                components_json=r["components_json"] or {},
                computed_at=r["computed_at"],
            )
            for r in rows
        ]

    # Recommendations ---------------------------------------------------
    def save_recommendation(
        self,
        recommendation: Recommendation,
        *,
        tenant_id: str,
        request_id: str,
        recommendation_id: str | None = None,
    ) -> str:
        from uuid import uuid4

        rid = recommendation_id or str(uuid4())
        with self._scoped_transaction(tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_recommendations (
                        recommendation_id, tenant_id, request_id,
                        recommended_quotation_id, recommended_supplier_id,
                        decision_band, composite_score, urgency_score, offer_score,
                        reasoning_markdown, alternatives_considered, risks_identified,
                        source
                    ) VALUES (
                        :recommendation_id, :tenant_id, :request_id,
                        :recommended_quotation_id, :recommended_supplier_id,
                        :decision_band, :composite_score, :urgency_score, :offer_score,
                        :reasoning_markdown, CAST(:alternatives AS JSONB),
                        CAST(:risks AS JSONB), :source
                    )
                    """
                ),
                {
                    "recommendation_id": rid,
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "recommended_quotation_id": recommendation.recommended_quotation_id,
                    "recommended_supplier_id": recommendation.recommended_supplier_id,
                    "decision_band": recommendation.decision_band,
                    "composite_score": recommendation.composite_score,
                    "urgency_score": recommendation.urgency_score,
                    "offer_score": recommendation.offer_score,
                    "reasoning_markdown": recommendation.reasoning_markdown,
                    "alternatives": _json_dumps([]),
                    "risks": _json_dumps([]),
                    "source": recommendation.source,
                },
            )
        return rid

    def get_latest_recommendation(
        self, request_id: str, *, tenant_id: str
    ) -> dict | None:
        with self._scoped_connection(tenant_id) as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT recommendation_id, tenant_id, request_id,
                               recommended_quotation_id, recommended_supplier_id,
                               decision_band, composite_score, urgency_score, offer_score,
                               reasoning_markdown, alternatives_considered, risks_identified,
                               source, generated_at
                        FROM procurement_recommendations
                        WHERE tenant_id = :tenant_id AND request_id = :request_id
                        ORDER BY generated_at DESC
                        LIMIT 1
                        """
                    ),
                    {"tenant_id": tenant_id, "request_id": request_id},
                )
                .mappings()
                .fetchone()
            )
        return dict(row) if row else None

    # Supplier performance history -------------------------------------
    def save_history_records(
        self, records: list[SupplierPerformanceRecord]
    ) -> int:
        if not records:
            return 0
        with self._engine.begin() as conn:
            for r in records:
                conn.execute(
                    text(
                        """
                        INSERT INTO procurement_supplier_performance_history (
                            history_id, tenant_id, supplier_id, quotation_id, category,
                            awarded_date, promised_delivery_date, actual_delivery_date,
                            delivered_on_time, days_delay, price_at_award, price_actual,
                            quality_score, notes
                        ) VALUES (
                            :history_id, :tenant_id, :supplier_id, :quotation_id, :category,
                            :awarded_date, :promised_delivery_date, :actual_delivery_date,
                            :delivered_on_time, :days_delay, :price_at_award, :price_actual,
                            :quality_score, :notes
                        )
                        ON CONFLICT (history_id) DO NOTHING
                        """
                    ),
                    {
                        "history_id": r.history_id,
                        "tenant_id": r.tenant_id,
                        "supplier_id": r.supplier_id,
                        "quotation_id": r.quotation_id,
                        "category": r.category,
                        "awarded_date": r.awarded_date,
                        "promised_delivery_date": r.promised_delivery_date,
                        "actual_delivery_date": r.actual_delivery_date,
                        "delivered_on_time": r.delivered_on_time,
                        "days_delay": r.days_delay,
                        "price_at_award": r.price_at_award,
                        "price_actual": r.price_actual,
                        "quality_score": r.quality_score,
                        "notes": r.notes,
                    },
                )
        return len(records)

    def list_history_for_supplier(
        self, supplier_id: str, *, tenant_id: str | None = None, limit: int = 200
    ) -> list[SupplierPerformanceRecord]:
        clauses = ["supplier_id = :supplier_id"]
        params: dict[str, Any] = {"supplier_id": supplier_id, "limit": limit}
        if tenant_id is not None:
            clauses.append("tenant_id = :tenant_id")
            params["tenant_id"] = tenant_id
        where = " AND ".join(clauses)
        with self._engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        f"""
                        SELECT history_id, tenant_id, supplier_id, quotation_id, category,
                               awarded_date, promised_delivery_date, actual_delivery_date,
                               delivered_on_time, days_delay, price_at_award, price_actual,
                               quality_score, notes, created_at
                        FROM procurement_supplier_performance_history
                        WHERE {where}
                        ORDER BY awarded_date DESC
                        LIMIT :limit
                        """
                    ),
                    params,
                )
                .mappings()
                .fetchall()
            )
        return [
            SupplierPerformanceRecord(
                history_id=r["history_id"],
                tenant_id=r["tenant_id"],
                supplier_id=r["supplier_id"],
                quotation_id=r["quotation_id"],
                category=r["category"],
                awarded_date=r["awarded_date"],
                promised_delivery_date=r["promised_delivery_date"],
                actual_delivery_date=r["actual_delivery_date"],
                delivered_on_time=r["delivered_on_time"],
                days_delay=r["days_delay"],
                price_at_award=r["price_at_award"],
                price_actual=r["price_actual"],
                quality_score=r["quality_score"],
                notes=r["notes"],
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # Negotiation messages ---------------------------------------------
    def save_negotiation_message(
        self,
        message: NegotiationMessage,
        *,
        tenant_id: str,
        request_id: str,
        quotation_id: str,
        supplier_id: str,
        message_id: str | None = None,
    ) -> str:
        from uuid import uuid4

        mid = message_id or str(uuid4())
        with self._scoped_transaction(tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_negotiation_messages (
                        message_id, tenant_id, request_id, quotation_id, supplier_id,
                        target_improvements, tone, message_text, source
                    ) VALUES (
                        :message_id, :tenant_id, :request_id, :quotation_id, :supplier_id,
                        CAST(:target_improvements AS JSONB), :tone, :message_text, :source
                    )
                    """
                ),
                {
                    "message_id": mid,
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                    "quotation_id": quotation_id,
                    "supplier_id": supplier_id,
                    "target_improvements": _json_dumps(message.target_improvements),
                    "tone": message.tone,
                    "message_text": message.message_text,
                    "source": message.source,
                },
            )
        return mid
