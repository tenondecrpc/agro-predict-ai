from __future__ import annotations

from backend.ml_models.models import AccuracyMetrics, Model, ModelStatus, ModelType, ModelValidation
from backend.ml_models.repository import ModelRepository


class ModelService:
    """Manages ML model lifecycle: registration, shadow mode, activation, rollback."""

    ACCURACY_THRESHOLD = 0.0  # accuracy_delta must be >= 0

    def __init__(self, *, repository: ModelRepository) -> None:
        self.repository = repository

    def register(
        self,
        version: str,
        model_type: ModelType,
        tenant_id: str,
        team_id: str,
        training_date: str,
        dataset_hash: str,
        accuracy_metrics: AccuracyMetrics,
        feature_schema: dict[str, str],
    ) -> Model:
        if not dataset_hash:
            raise ValueError("dataset_hash is required")

        model = Model(
            version=version,
            model_type=model_type,
            tenant_id=tenant_id,
            team_id=team_id,
            training_date=training_date,
            dataset_hash=dataset_hash,
            accuracy_metrics=accuracy_metrics,
            feature_schema=feature_schema,
        )

        # Flag for review if accuracy is low
        if accuracy_metrics.r2_score is not None and accuracy_metrics.r2_score < 0.5:
            model.status = ModelStatus.REGISTERED  # stays registered, requires review

        self.repository.save_model(model)
        return model

    def promote_to_shadow(self, model_id: str, *, tenant_id: str) -> Model:
        model = self.repository.get_model(model_id, tenant_id=tenant_id)
        if model is None:
            raise ValueError("Model not found")
        model.promote_to_shadow()
        self.repository.save_model(model)
        return model

    def activate(self, model_id: str, *, tenant_id: str) -> Model:
        model = self.repository.get_model(model_id, tenant_id=tenant_id)
        if model is None:
            raise ValueError("Model not found")

        # Deactivate current active model
        current = self.repository.get_active_model(tenant_id)
        if current is not None:
            current.archive()
            self.repository.save_model(current)

        model.activate()
        self.repository.save_model(model)
        return model

    def rollback(self, tenant_id: str) -> Model | None:
        models = self.repository.list_models(tenant_id)
        active = next((m for m in models if m.status.value == "active"), None)
        if active is None:
            raise ValueError("No active model to rollback from")

        # Find previous version
        previous = None
        for m in sorted(
            [x for x in models if x.status.value == "archived"],
            key=lambda x: x.created_at,
            reverse=True,
        ):
            previous = m
            break

        if previous is None:
            raise ValueError("No previous model version to rollback to")

        active.archive()
        self.repository.save_model(active)
        previous.activate()
        self.repository.save_model(previous)
        return previous

    def create_shadow_validation(
        self,
        shadow_model_id: str,
        *,
        tenant_id: str,
    ) -> ModelValidation:
        active = self.repository.get_active_model(tenant_id)
        if active is None:
            raise ValueError("No active model for comparison")

        validation = ModelValidation(
            model_id=active.model_id,
            shadow_model_id=shadow_model_id,
        )
        self.repository.save_validation(validation)
        return validation

    def complete_validation(
        self,
        validation_id: str,
        accuracy_delta: float,
        comparison: dict[str, object],
    ) -> ModelValidation:
        validation = self.repository.get_validation(validation_id)
        if validation is None:
            raise ValueError("Validation not found")

        validation.complete(accuracy_delta, comparison)
        self.repository.save_validation(validation)
        return validation

    def can_promote(self, model_id: str, *, tenant_id: str) -> bool:
        """Check whether a shadow model meets the accuracy threshold for promotion.

        A model can be promoted when:
        1. It exists and is in shadow status.
        2. Its r2_score meets or exceeds ACCURACY_THRESHOLD (default 0.0).
        """
        model = self.repository.get_model(model_id, tenant_id=tenant_id)
        if model is None:
            return False
        if model.status.value != "shadow":
            return False
        r2 = model.accuracy_metrics.r2_score
        if r2 is None:
            return False
        return r2 >= self.ACCURACY_THRESHOLD

    def get_model(self, model_id: str, *, tenant_id: str) -> Model | None:
        return self.repository.get_model(model_id, tenant_id=tenant_id)

    def list_models(self, tenant_id: str) -> list[Model]:
        return self.repository.list_models(tenant_id)

    def get_active_model(self, tenant_id: str) -> Model | None:
        return self.repository.get_active_model(tenant_id)

    def get_shadow_model(self, tenant_id: str) -> Model | None:
        return self.repository.get_shadow_model(tenant_id)

    def archive(self, model_id: str, *, tenant_id: str) -> Model | None:
        model = self.repository.get_model(model_id, tenant_id=tenant_id)
        if model is None:
            return None
        model.archive()
        self.repository.save_model(model)
        return model

    def promote_to_active(
        self, model_id: str, *, tenant_id: str, promoted_by: str | None = None
    ) -> Model | None:
        """Promote a model to active, archiving the current active model."""
        result = self.repository.promote_to_active(
            model_id, tenant_id=tenant_id, promoted_by=promoted_by
        )
        if result is None:
            raise ValueError("Model not found")
        return result
