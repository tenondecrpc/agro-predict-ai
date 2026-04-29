"""Agent execution repository for health metrics and observability.

Stores per-agent execution records and provides windowed health metrics
used by the /api/v1/agents/health endpoint.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from statistics import quantiles as statistics_quantiles
from typing import Protocol, runtime_checkable
from uuid import uuid4

from sqlalchemy import Engine, create_engine, text

logger = logging.getLogger(__name__)


@dataclass
class AgentExecutionRecord:
    """A single agent execution event."""

    execution_id: str = field(default_factory=lambda: str(uuid4()))
    prediction_id: str = ""
    tenant_id: str = ""
    agent_name: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    duration_ms: int | None = None
    status: str = "success"
    error_message: str | None = None
    degradation_flags: list[str] = field(default_factory=list)


@dataclass
class AgentHealthMetrics:
    """Windowed health metrics for a single agent."""

    total_executions: int
    error_count: int
    p95_latency_ms: float | None
    last_executed_at: datetime | None

    @property
    def error_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return self.error_count / self.total_executions

    @property
    def status(self) -> str:
        if self.total_executions == 0:
            return "unknown"
        if self.error_rate > 0.5:
            return "error"
        if self.error_rate > 0.1:
            return "degraded"
        return "healthy"


@runtime_checkable
class AgentExecutionRepositoryProtocol(Protocol):
    def save(self, record: AgentExecutionRecord) -> None: ...

    def get_health_metrics(
        self,
        tenant_id: str,
        agent_name: str,
        window_minutes: int = 15,
    ) -> AgentHealthMetrics: ...


class InMemoryAgentExecutionRepository:
    """In-memory implementation for testing and development."""

    def __init__(self) -> None:
        self._records: list[AgentExecutionRecord] = []

    def save(self, record: AgentExecutionRecord) -> None:
        self._records.append(record)

    def get_health_metrics(
        self,
        tenant_id: str,
        agent_name: str,
        window_minutes: int = 15,
    ) -> AgentHealthMetrics:
        cutoff = datetime.now(UTC) - timedelta(minutes=window_minutes)
        window_records = [
            r
            for r in self._records
            if r.tenant_id == tenant_id
            and r.agent_name == agent_name
            and r.started_at >= cutoff
        ]

        if not window_records:
            return AgentHealthMetrics(
                total_executions=0,
                error_count=0,
                p95_latency_ms=None,
                last_executed_at=None,
            )

        error_count = sum(1 for r in window_records if r.status in ("failure", "error"))
        last_executed_at = max(r.started_at for r in window_records)

        latencies = [r.duration_ms for r in window_records if r.duration_ms is not None]
        p95_latency_ms: float | None = None
        if latencies:
            latencies_sorted = sorted(latencies)
            if len(latencies_sorted) >= 2:
                quants = statistics_quantiles(latencies_sorted, n=100)
                p95_latency_ms = float(quants[94])
            else:
                p95_latency_ms = float(latencies_sorted[-1])

        return AgentHealthMetrics(
            total_executions=len(window_records),
            error_count=error_count,
            p95_latency_ms=p95_latency_ms,
            last_executed_at=last_executed_at,
        )


class PostgresAgentExecutionRepository:
    """PostgreSQL-backed agent execution repository."""

    def __init__(
        self,
        database_url: str,
        *,
        engine: Engine | None = None,
    ) -> None:
        self._engine = engine or create_engine(database_url, future=True, pool_pre_ping=True)

    def save(self, record: AgentExecutionRecord) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO agent_executions
                        (execution_id, prediction_id, tenant_id, agent_name,
                         started_at, completed_at, duration_ms, status,
                         error_message, degradation_flags)
                    VALUES
                        (:execution_id, :prediction_id, :tenant_id, :agent_name,
                         :started_at, :completed_at, :duration_ms, :status,
                         :error_message, :degradation_flags)
                    ON CONFLICT (execution_id) DO NOTHING
                    """
                ),
                {
                    "execution_id": record.execution_id,
                    "prediction_id": record.prediction_id,
                    "tenant_id": record.tenant_id,
                    "agent_name": record.agent_name,
                    "started_at": record.started_at,
                    "completed_at": record.completed_at,
                    "duration_ms": record.duration_ms,
                    "status": record.status,
                    "error_message": record.error_message,
                    "degradation_flags": json.dumps(record.degradation_flags),
                },
            )

    def get_health_metrics(
        self,
        tenant_id: str,
        agent_name: str,
        window_minutes: int = 15,
    ) -> AgentHealthMetrics:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total,
                        SUM(CASE WHEN status IN ('failure', 'error') THEN 1 ELSE 0 END) AS errors,
                        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) AS p95_ms,
                        MAX(started_at) AS last_executed_at
                    FROM agent_executions
                    WHERE tenant_id = :tenant_id
                      AND agent_name = :agent_name
                      AND started_at >= NOW() - INTERVAL ':window_minutes minutes'
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "agent_name": agent_name,
                    "window_minutes": window_minutes,
                },
            ).fetchone()

        if row is None or row[0] == 0:
            return AgentHealthMetrics(
                total_executions=0,
                error_count=0,
                p95_latency_ms=None,
                last_executed_at=None,
            )

        return AgentHealthMetrics(
            total_executions=int(row[0]),
            error_count=int(row[1] or 0),
            p95_latency_ms=float(row[2]) if row[2] is not None else None,
            last_executed_at=row[3],
        )
