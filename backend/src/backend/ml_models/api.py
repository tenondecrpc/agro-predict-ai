from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.ml_models.models import AccuracyMetrics, Model, ModelType, ModelValidation
from backend.ml_models.service import ModelService


def build_models_router(service: ModelService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/models", tags=["ml-models"])

    @router.post("", response_model=Model)
    def register_model(
        version: str,
        model_type: ModelType,
        tenant_id: str,
        team_id: str,
        training_date: str,
        dataset_hash: str,
        accuracy_metrics: AccuracyMetrics,
        feature_schema: dict[str, str],
    ) -> Model:
        try:
            return service.register(
                version=version,
                model_type=model_type,
                tenant_id=tenant_id,
                team_id=team_id,
                training_date=training_date,
                dataset_hash=dataset_hash,
                accuracy_metrics=accuracy_metrics,
                feature_schema=feature_schema,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("", response_model=list[Model])
    def list_models(tenant_id: str) -> list[Model]:
        return service.list_models(tenant_id)

    @router.get("/active", response_model=Model | None)
    def get_active_model(tenant_id: str) -> Model | None:
        return service.get_active_model(tenant_id)

    @router.post("/{model_id}/shadow", response_model=Model)
    def promote_to_shadow(model_id: str, tenant_id: str) -> Model:
        try:
            return service.promote_to_shadow(model_id, tenant_id=tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/{model_id}/activate", response_model=Model)
    def activate_model(model_id: str, tenant_id: str) -> Model:
        try:
            return service.activate(model_id, tenant_id=tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/{model_id}/promote-to-active", response_model=Model)
    def promote_to_active(model_id: str, tenant_id: str, promoted_by: str | None = None) -> Model:
        try:
            result = service.promote_to_active(model_id, tenant_id=tenant_id, promoted_by=promoted_by)
            if result is None:
                raise HTTPException(status_code=404, detail="Model not found")
            return result
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/{model_id}/archive", response_model=Model)
    def archive_model(model_id: str, tenant_id: str) -> Model:
        try:
            result = service.archive(model_id, tenant_id=tenant_id)
            if result is None:
                raise HTTPException(status_code=404, detail="Model not found")
            return result
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/rollback", response_model=Model)
    def rollback(tenant_id: str) -> Model:
        try:
            result = service.rollback(tenant_id)
            if result is None:
                raise HTTPException(status_code=400, detail="Rollback failed")
            return result
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/validations", response_model=ModelValidation)
    def create_validation(shadow_model_id: str, tenant_id: str) -> ModelValidation:
        try:
            return service.create_shadow_validation(shadow_model_id, tenant_id=tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return router
