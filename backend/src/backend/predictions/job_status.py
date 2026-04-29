"""JobStatus model for async prediction run tracking via Redis.

The worker writes status updates to Redis hash keys under job:{run_id}.
The API reads them to serve GET /api/v1/predictions/{run_id}/status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class JobStatus:
    """Mutable job status written to Redis by the ARQ worker."""

    run_id: str
    tenant_id: str
    status: Literal["queued", "running", "completed", "failed"] = "queued"
    current_node: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    prediction_id: str | None = None
    progress_pct: int = 0

    _NODE_PROGRESS: dict[str, int] = field(
        default_factory=lambda: {
            "data_analyst": 10,
            "ml_executor": 40,
            "recommendation_engine": 60,
            "explainability": 80,
            "reviewer": 95,
            "completed": 100,
        },
        repr=False,
    )

    def to_redis_hash(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "current_node": self.current_node or "",
            "started_at": self.started_at.isoformat() if self.started_at else "",
            "completed_at": self.completed_at.isoformat() if self.completed_at else "",
            "error_message": self.error_message or "",
            "prediction_id": self.prediction_id or "",
            "progress_pct": str(self.progress_pct),
        }

    @classmethod
    def from_redis_hash(cls, data: dict[str, str]) -> JobStatus:
        started_at = None
        completed_at = None
        if data.get("started_at"):
            try:
                started_at = datetime.fromisoformat(data["started_at"])
            except ValueError:
                pass
        if data.get("completed_at"):
            try:
                completed_at = datetime.fromisoformat(data["completed_at"])
            except ValueError:
                pass

        return cls(
            run_id=data.get("run_id", ""),
            tenant_id=data.get("tenant_id", ""),
            status=data.get("status", "queued"),  # type: ignore[arg-type]
            current_node=data.get("current_node") or None,
            started_at=started_at,
            completed_at=completed_at,
            error_message=data.get("error_message") or None,
            prediction_id=data.get("prediction_id") or None,
            progress_pct=int(data.get("progress_pct", "0")),
        )

    def to_response_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "current_node": self.current_node,
            "progress_pct": self.progress_pct,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "prediction_id": self.prediction_id,
        }
