from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.data_ingestion.models import DataQualitySummary, DataRecord, IngestionBatch, IngestionSummary
from backend.data_ingestion.service import IngestionService


def build_data_router(service: IngestionService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/data", tags=["data-ingestion"])

    @router.post("/ingest", response_model=DataRecord)
    def ingest_single(
        source_id: str,
        tenant_id: str,
        team_id: str,
        payload: dict[str, object],
    ) -> DataRecord:
        try:
            return service.ingest_single(source_id, tenant_id, team_id, payload)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.post("/ingest/batch", response_model=IngestionSummary)
    def ingest_batch(batch: IngestionBatch) -> IngestionSummary:
        try:
            return service.ingest_batch(batch)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/quality", response_model=DataQualitySummary)
    def get_quality(tenant_id: str) -> DataQualitySummary:
        return service.get_quality_summary(tenant_id)

    @router.get("/records", response_model=list[DataRecord])
    def list_records(tenant_id: str) -> list[DataRecord]:
        return service.list_records(tenant_id)

    @router.get("/records/{record_id}", response_model=DataRecord)
    def get_record(record_id: str, tenant_id: str) -> DataRecord:
        rec = service.get_record(record_id, tenant_id=tenant_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="Record not found")
        return rec

    return router
