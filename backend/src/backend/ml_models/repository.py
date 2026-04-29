from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from sqlalchemy import Engine, create_engine, text

from backend.ml_models.models import Model, ModelValidation

logger = logging.getLogger(__name__)


@runtime_checkable
class ModelRepository(Protocol):
    def save_model(self, model: Model) -> Model: ...

    def get_model(self, model_id: str, *, tenant_id: str) -> Model | None: ...

    def list_models(self, tenant_id: str) -> list[Model]: ...

    def get_active_model(self, tenant_id: str) -> Model | None: ...

    def get_shadow_model(self, tenant_id: str) -> Model | None: ...

    def promote_to_active(
        self, model_id: str, *, tenant_id: str, promoted_by: str | None = None
    ) -> Model | None: ...

    def promote_to_shadow(
        self, model_id: str, *, tenant_id: str, promoted_by: str | None = None
    ) -> Model | None: ...

    def archive(self, model_id: str, *, tenant_id: str) -> Model | None: ...

    def save_validation(self, validation: ModelValidation) -> ModelValidation: ...

    def get_validation(self, validation_id: str) -> ModelValidation | None: ...


class InMemoryModelRepository:
    def __init__(self) -> None:
        self._models: dict[str, Model] = {}
        self._validations: dict[str, ModelValidation] = {}

    def save_model(self, model: Model) -> Model:
        self._models[model.model_id] = model.model_copy(deep=True)
        return model

    def get_model(self, model_id: str, *, tenant_id: str) -> Model | None:
        m = self._models.get(model_id)
        if m is None or m.tenant_id != tenant_id:
            return None
        return m.model_copy(deep=True)

    def list_models(self, tenant_id: str) -> list[Model]:
        return [m.model_copy(deep=True) for m in self._models.values() if m.tenant_id == tenant_id]

    def get_active_model(self, tenant_id: str) -> Model | None:
        for m in self._models.values():
            if m.tenant_id == tenant_id and m.status.value == "active":
                return m.model_copy(deep=True)
        return None

    def get_shadow_model(self, tenant_id: str) -> Model | None:
        for m in self._models.values():
            if m.tenant_id == tenant_id and m.status.value == "shadow":
                return m.model_copy(deep=True)
        return None

    def promote_to_active(
        self, model_id: str, *, tenant_id: str, promoted_by: str | None = None
    ) -> Model | None:
        model = self._models.get(model_id)
        if model is None or model.tenant_id != tenant_id:
            return None
        # Archive current active
        for m in self._models.values():
            if m.tenant_id == tenant_id and m.status.value == "active":
                m.archive()
        model.activate()
        return model.model_copy(deep=True)

    def promote_to_shadow(
        self, model_id: str, *, tenant_id: str, promoted_by: str | None = None
    ) -> Model | None:
        model = self._models.get(model_id)
        if model is None or model.tenant_id != tenant_id:
            return None
        model.promote_to_shadow()
        return model.model_copy(deep=True)

    def archive(self, model_id: str, *, tenant_id: str) -> Model | None:
        model = self._models.get(model_id)
        if model is None or model.tenant_id != tenant_id:
            return None
        model.archive()
        return model.model_copy(deep=True)

    def save_validation(self, validation: ModelValidation) -> ModelValidation:
        self._validations[validation.validation_id] = validation.model_copy(deep=True)
        return validation

    def get_validation(self, validation_id: str) -> ModelValidation | None:
        v = self._validations.get(validation_id)
        return v.model_copy(deep=True) if v else None


class PostgresModelRepository:
    """PostgreSQL-backed model repository implementing the ModelRepository protocol."""

    def __init__(
        self,
        database_url: str,
        *,
        engine: Engine | None = None,
    ) -> None:
        self._engine = engine or create_engine(database_url, future=True, pool_pre_ping=True)

    # -- Model operations ---------------------------------------------------

    def save_model(self, model: Model) -> Model:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO model_registry
                        (model_id, crop, model_type, version, artifact_path, dataset_hash,
                         trained_at, mae, rmse, r2, feature_schema, status, promoted_at,
                         promoted_by, created_at)
                    VALUES
                        (:model_id, :crop, :model_type, :version, :artifact_path, :dataset_hash,
                         :trained_at, :mae, :rmse, :r2, :feature_schema, :status, :promoted_at,
                         :promoted_by, :created_at)
                    ON CONFLICT (model_id) DO UPDATE SET
                        crop = EXCLUDED.crop,
                        model_type = EXCLUDED.model_type,
                        version = EXCLUDED.version,
                        artifact_path = EXCLUDED.artifact_path,
                        dataset_hash = EXCLUDED.dataset_hash,
                        trained_at = EXCLUDED.trained_at,
                        mae = EXCLUDED.mae,
                        rmse = EXCLUDED.rmse,
                        r2 = EXCLUDED.r2,
                        feature_schema = EXCLUDED.feature_schema,
                        status = EXCLUDED.status,
                        promoted_at = EXCLUDED.promoted_at,
                        promoted_by = EXCLUDED.promoted_by,
                        created_at = EXCLUDED.created_at
                    """
                ),
                self._model_to_params(model),
            )
        return model

    def get_model(self, model_id: str, *, tenant_id: str) -> Model | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT model_id, crop, model_type, version, artifact_path, dataset_hash,
                           trained_at, mae, rmse, r2, feature_schema, status, promoted_at,
                           promoted_by, created_at
                    FROM model_registry
                    WHERE model_id = :model_id AND crop = :tenant_id
                    """
                ),
                {"model_id": model_id, "tenant_id": tenant_id},
            ).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def list_models(self, tenant_id: str) -> list[Model]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT model_id, crop, model_type, version, artifact_path, dataset_hash,
                           trained_at, mae, rmse, r2, feature_schema, status, promoted_at,
                           promoted_by, created_at
                    FROM model_registry
                    WHERE crop = :tenant_id
                    ORDER BY created_at DESC
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchall()
        return [self._row_to_model(r) for r in rows]

    def get_active_model(self, tenant_id: str) -> Model | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT model_id, crop, model_type, version, artifact_path, dataset_hash,
                           trained_at, mae, rmse, r2, feature_schema, status, promoted_at,
                           promoted_by, created_at
                    FROM model_registry
                    WHERE crop = :tenant_id AND status = 'active'
                    ORDER BY promoted_at DESC
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def get_shadow_model(self, tenant_id: str) -> Model | None:
        """Return the current shadow model for a tenant."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT model_id, crop, model_type, version, artifact_path, dataset_hash,
                           trained_at, mae, rmse, r2, feature_schema, status, promoted_at,
                           promoted_by, created_at
                    FROM model_registry
                    WHERE crop = :tenant_id AND status = 'shadow'
                    ORDER BY promoted_at DESC
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id},
            ).fetchone()
        if row is None:
            return None
        return self._row_to_model(row)

    def promote_to_active(self, model_id: str, *, tenant_id: str, promoted_by: str | None = None) -> Model | None:
        """Promote a model to active status, archiving the current active model."""
        now = datetime.now(UTC)
        with self._engine.begin() as conn:
            # Archive current active model for this tenant
            conn.execute(
                text(
                    """
                    UPDATE model_registry
                    SET status = 'archived'
                    WHERE crop = :tenant_id AND status = 'active'
                    """
                ),
                {"tenant_id": tenant_id},
            )
            # Promote the target model
            result = conn.execute(
                text(
                    """
                    UPDATE model_registry
                    SET status = 'active', promoted_at = :promoted_at, promoted_by = :promoted_by
                    WHERE model_id = :model_id AND crop = :tenant_id
                    RETURNING model_id, crop, model_type, version, artifact_path, dataset_hash,
                              trained_at, mae, rmse, r2, feature_schema, status, promoted_at,
                              promoted_by, created_at
                    """
                ),
                {"model_id": model_id, "tenant_id": tenant_id, "promoted_at": now, "promoted_by": promoted_by},
            ).fetchone()
        if result is None:
            return None
        return self._row_to_model(result)

    def promote_to_shadow(self, model_id: str, *, tenant_id: str, promoted_by: str | None = None) -> Model | None:
        """Promote a registered model to shadow status."""
        now = datetime.now(UTC)
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE model_registry
                    SET status = 'shadow', promoted_at = :promoted_at, promoted_by = :promoted_by
                    WHERE model_id = :model_id AND crop = :tenant_id
                    RETURNING model_id, crop, model_type, version, artifact_path, dataset_hash,
                              trained_at, mae, rmse, r2, feature_schema, status, promoted_at,
                              promoted_by, created_at
                    """
                ),
                {"model_id": model_id, "tenant_id": tenant_id, "promoted_at": now, "promoted_by": promoted_by},
            ).fetchone()
        if result is None:
            return None
        return self._row_to_model(result)

    def archive(self, model_id: str, *, tenant_id: str) -> Model | None:
        """Archive a model."""
        with self._engine.begin() as conn:
            result = conn.execute(
                text(
                    """
                    UPDATE model_registry
                    SET status = 'archived'
                    WHERE model_id = :model_id AND crop = :tenant_id
                    RETURNING model_id, crop, model_type, version, artifact_path, dataset_hash,
                              trained_at, mae, rmse, r2, feature_schema, status, promoted_at,
                              promoted_by, created_at
                    """
                ),
                {"model_id": model_id, "tenant_id": tenant_id},
            ).fetchone()
        if result is None:
            return None
        return self._row_to_model(result)

    # -- Validation operations ----------------------------------------------

    def save_validation(self, validation: ModelValidation) -> ModelValidation:
        # Validations are kept in-memory for now; the shadow_comparisons table
        # stores the per-pcomparison records.
        return validation

    def get_validation(self, validation_id: str) -> ModelValidation | None:
        return None

    # -- Internal helpers ---------------------------------------------------

    @staticmethod
    def _model_to_params(model: Model) -> dict:
        metrics = model.accuracy_metrics
        return {
            "model_id": model.model_id,
            "crop": model.tenant_id,
            "model_type": model.model_type.value,
            "version": model.version,
            "artifact_path": "",
            "dataset_hash": model.dataset_hash,
            "trained_at": model.training_date,
            "mae": metrics.mae,
            "rmse": metrics.rmse,
            "r2": metrics.r2_score,
            "feature_schema": json.dumps(model.feature_schema),
            "status": model.status.value,
            "promoted_at": model.activated_at,
            "promoted_by": None,
            "created_at": model.created_at,
        }

    @staticmethod
    def _row_to_model(row) -> Model:
        from backend.ml_models.models import AccuracyMetrics, ModelStatus, ModelType

        feature_schema = row[10]
        if isinstance(feature_schema, str):
            feature_schema = json.loads(feature_schema)

        status_value = row[11]
        try:
            status = ModelStatus(status_value)
        except ValueError:
            status = ModelStatus.REGISTERED

        return Model(
            model_id=row[0],
            version=row[3],
            model_type=ModelType(row[2]),
            tenant_id=row[1],
            team_id="",
            training_date=row[6] or datetime.now(UTC),
            dataset_hash=row[5],
            accuracy_metrics=AccuracyMetrics(
                r2_score=row[9],
                rmse=row[8],
                mae=row[7],
            ),
            feature_schema=feature_schema or {},
            status=status,
            created_at=row[14] or datetime.now(UTC),
            activated_at=row[12],
        )
