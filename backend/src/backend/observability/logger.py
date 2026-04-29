from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


class StructuredLogger:
    """Emits structured JSON logs for agent executions and predictions."""

    def __init__(self, *, service_name: str = "agropredict") -> None:
        self.service_name = service_name

    def log_agent_execution(
        self,
        *,
        tenant_id: str,
        prediction_id: str,
        agent_name: str,
        duration_ms: int,
        status: str,
        error_message: str | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "error" if error_message else "info",
            "service": self.service_name,
            "tenant_id": tenant_id,
            "prediction_id": prediction_id,
            "agent_name": agent_name,
            "duration_ms": duration_ms,
            "status": status,
            "trace_id": trace_id,
        }
        if error_message:
            entry["error_message"] = error_message
        print(json.dumps(entry))
        return entry

    def log_prediction(
        self,
        *,
        tenant_id: str,
        prediction_id: str,
        model_version: str,
        status: str,
        duration_ms: int,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": "info",
            "service": self.service_name,
            "tenant_id": tenant_id,
            "prediction_id": prediction_id,
            "model_version": model_version,
            "status": status,
            "duration_ms": duration_ms,
            "trace_id": trace_id,
        }
        print(json.dumps(entry))
        return entry
