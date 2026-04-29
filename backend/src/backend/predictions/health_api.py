"""Agent health endpoint for AgroPredict AI.

Exposes per-agent execution metrics over a sliding 15-minute window.
Requires tenant_id query parameter for tenant-scoped metrics.

GET /api/v1/agents/health?tenant_id=X
"""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.predictions.agent_execution_repository import (
    AgentExecutionRepositoryProtocol,
    AgentHealthMetrics,
)

_AGENT_NAMES = [
    "data_analyst",
    "ml_executor",
    "recommendation_engine",
    "explainability",
    "reviewer",
]


def _metrics_to_dict(metrics: AgentHealthMetrics) -> dict:
    return {
        "status": metrics.status,
        "last_executed_at": metrics.last_executed_at.isoformat() if metrics.last_executed_at else None,
        "p95_latency_ms": metrics.p95_latency_ms,
        "error_rate_15m": round(metrics.error_rate, 4),
        "total_executions_15m": metrics.total_executions,
        "active_degradation_flags": [],
    }


def build_agent_health_router(
    repository: AgentExecutionRepositoryProtocol | None = None,
) -> APIRouter:
    """Build the agents health router, injecting the given repository.

    When no repository is provided, health metrics will be unavailable
    (all agents show 'unknown' status with zero executions).
    """
    repo = repository
    router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

    @router.get("/health")
    def get_agent_health(
        tenant_id: str = Query(..., description="Tenant ID for scoped metrics"),
    ) -> dict:
        agents_health: dict[str, dict] = {}
        for agent_name in _AGENT_NAMES:
            metrics = repo.get_health_metrics(tenant_id, agent_name, window_minutes=15)
            agents_health[agent_name] = _metrics_to_dict(metrics)
        return {"agents": agents_health}

    return router
