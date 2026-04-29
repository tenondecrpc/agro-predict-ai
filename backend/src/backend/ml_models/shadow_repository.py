"""Shadow comparison repository for model validation."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Engine, create_engine, text

logger = logging.getLogger(__name__)


class ShadowComparisonRepository:
    """PostgreSQL-backed shadow comparison repository."""

    def __init__(
        self,
        database_url: str,
        *,
        engine: Engine | None = None,
    ) -> None:
        self._engine = engine or create_engine(database_url, future=True, pool_pre_ping=True)

    def save_comparison(
        self,
        prediction_id: str,
        active_version: str,
        shadow_version: str,
        active_output: dict,
        shadow_output: dict,
    ) -> None:
        """Save a shadow comparison record."""
        delta_pct = 0.0
        active_val = active_output.get("point_estimate", 0)
        shadow_val = shadow_output.get("point_estimate", 0)
        if active_val != 0:
            delta_pct = abs(shadow_val - active_val) / abs(active_val) * 100

        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO shadow_comparisons
                        (comparison_id, prediction_id, active_version, shadow_version,
                         active_output, shadow_output, delta_pct, recorded_at)
                    VALUES
                        (:comparison_id, :prediction_id, :active_version, :shadow_version,
                         :active_output, :shadow_output, :delta_pct, :recorded_at)
                    """
                ),
                {
                    "comparison_id": str(uuid4()),
                    "prediction_id": prediction_id,
                    "active_version": active_version,
                    "shadow_version": shadow_version,
                    "active_output": json.dumps(active_output),
                    "shadow_output": json.dumps(shadow_output),
                    "delta_pct": round(delta_pct, 4),
                    "recorded_at": datetime.now(UTC),
                },
            )
