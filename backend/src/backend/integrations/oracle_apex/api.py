from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.integrations.oracle_apex.models import OracleAPEXConnection, SyncJob, WriteBackAudit, WriteBackRequest
from backend.integrations.oracle_apex.service import APEXService


def build_apex_router(service: APEXService) -> APIRouter:
    router = APIRouter(prefix="/api/v1/apex", tags=["oracle-apex"])

    @router.post("/connections", response_model=OracleAPEXConnection)
    def create_connection(
        endpoint: str,
        credentials_ref: str,
        tenant_id: str = "default",
        sync_schedule: str = "0 * * * *",
    ) -> OracleAPEXConnection:
        return service.create_connection(
            endpoint,
            credentials_ref,
            tenant_id=tenant_id,
            sync_schedule=sync_schedule,
        )

    @router.get("/connections/{connection_id}", response_model=OracleAPEXConnection | None)
    def get_connection(connection_id: str, tenant_id: str = "default") -> OracleAPEXConnection | None:
        return service.get_connection(connection_id, tenant_id=tenant_id)

    @router.post("/sync", response_model=SyncJob)
    def sync_data(
        connection_id: str,
        tenant_id: str,
    ) -> SyncJob:
        try:
            return service.sync_data(connection_id, tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.post("/writeback", response_model=WriteBackAudit)
    def write_back(request: WriteBackRequest, tenant_id: str) -> WriteBackAudit:
        try:
            return service.write_back(request, tenant_id=tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/circuit/{connection_id}")
    def get_circuit_state(connection_id: str, tenant_id: str = "default") -> dict[str, object]:
        try:
            return service.get_circuit_state(connection_id, tenant_id=tenant_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @router.get("/audits", response_model=list[WriteBackAudit])
    def list_audits(tenant_id: str) -> list[WriteBackAudit]:
        return service.list_audits(tenant_id)

    return router
