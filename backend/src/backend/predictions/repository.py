from __future__ import annotations

import json
import logging
from typing import Protocol, runtime_checkable

from sqlalchemy import Engine, create_engine, text

from backend.predictions.models import PredictionOutput


@runtime_checkable
class PredictionRepository(Protocol):
    def save(self, prediction: PredictionOutput) -> PredictionOutput: ...

    def get_by_id(self, prediction_id: str, *, tenant_id: str) -> PredictionOutput | None: ...

    def list_by_tenant(self, tenant_id: str) -> list[PredictionOutput]: ...

    def get_dead_letter_record(self, run_id: str, *, tenant_id: str) -> dict | None: ...

    def archive_dead_letter_record(self, run_id: str, *, tenant_id: str) -> None: ...

    def list_failed_predictions(self, tenant_id: str) -> list[PredictionOutput]: ...


class InMemoryPredictionRepository:
    def __init__(self) -> None:
        self._store: dict[str, PredictionOutput] = {}

    def save(self, prediction: PredictionOutput) -> PredictionOutput:
        self._store[prediction.prediction_id] = prediction.model_copy(deep=True)
        return prediction

    def get_by_id(self, prediction_id: str, *, tenant_id: str) -> PredictionOutput | None:
        prediction = self._store.get(prediction_id)
        if prediction is None or prediction.tenant_id != tenant_id:
            return None
        return prediction.model_copy(deep=True)

    def list_by_tenant(self, tenant_id: str) -> list[PredictionOutput]:
        return [
            p.model_copy(deep=True)
            for p in self._store.values()
            if p.tenant_id == tenant_id
        ]

    def get_dead_letter_record(self, run_id: str, *, tenant_id: str) -> dict | None:
        return None

    def archive_dead_letter_record(self, run_id: str, *, tenant_id: str) -> None:
        pass

    def list_failed_predictions(self, tenant_id: str) -> list[PredictionOutput]:
        return []


class PostgresPredictionRepository:
    """PostgreSQL-backed prediction repository with tenant-scoped queries."""

    def __init__(
        self,
        database_url: str,
        *,
        engine: Engine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._engine = engine or create_engine(database_url, future=True, pool_pre_ping=True)
        self._logger = logger or logging.getLogger(__name__)

    def save(self, prediction: PredictionOutput) -> PredictionOutput:
        """Save a prediction output to PostgreSQL.

        Note: This requires the predictions table to exist.
        For now, predictions are stored as JSONB in a simple table.
        """
        payload = prediction.model_dump(mode="json")
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO predictions (prediction_id, tenant_id, team_id, payload)
                    VALUES (:prediction_id, :tenant_id, :team_id, :payload)
                    ON CONFLICT (prediction_id) DO UPDATE
                    SET tenant_id = :tenant_id,
                        team_id = :team_id,
                        payload = :payload,
                        updated_at = NOW()
                    """
                ),
                {
                    "prediction_id": prediction.prediction_id,
                    "tenant_id": prediction.tenant_id,
                    "team_id": prediction.team_id,
                    "payload": json.dumps(payload),
                },
            )
        return prediction

    def get_by_id(self, prediction_id: str, *, tenant_id: str) -> PredictionOutput | None:
        """Retrieve a prediction by ID, scoped to tenant."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT payload FROM predictions
                    WHERE prediction_id = :prediction_id AND tenant_id = :tenant_id
                    """
                ),
                {"prediction_id": prediction_id, "tenant_id": tenant_id},
            ).fetchone()
        if row is None:
            return None
        return PredictionOutput.model_validate(json.loads(row[0]))

    def list_by_tenant(self, tenant_id: str) -> list[PredictionOutput]:
        """List all predictions for a tenant."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT payload FROM predictions
                    WHERE tenant_id = :tenant_id
                    ORDER BY created_at DESC
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchall()
        return [PredictionOutput.model_validate(json.loads(row[0])) for row in rows]

    def get_dead_letter_record(self, run_id: str, *, tenant_id: str) -> dict | None:
        """Retrieve a dead letter record for retry."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT payload FROM dead_letter_queue
                    WHERE run_id = :run_id AND tenant_id = :tenant_id
                    AND archived = false
                    """
                ),
                {"run_id": run_id, "tenant_id": tenant_id},
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def archive_dead_letter_record(self, run_id: str, *, tenant_id: str) -> None:
        """Archive a dead letter record after successful retry."""
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    UPDATE dead_letter_queue
                    SET archived = true, archived_at = NOW()
                    WHERE run_id = :run_id AND tenant_id = :tenant_id
                    """
                ),
                {"run_id": run_id, "tenant_id": tenant_id},
            )

    def list_failed_predictions(self, tenant_id: str) -> list[PredictionOutput]:
        """List failed predictions for a tenant."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT payload FROM predictions
                    WHERE tenant_id = :tenant_id
                    AND payload->>'status' = 'failed'
                    ORDER BY created_at DESC
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchall()
        return [PredictionOutput.model_validate(json.loads(row[0])) for row in rows]
