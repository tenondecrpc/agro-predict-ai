from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import uuid4

from backend.integrations.oracle_apex.adapter import OracleAPEXAdapter
from backend.integrations.oracle_apex.models import (
    APEXFieldRecord,
    CircuitBreakerState,
    OracleAPEXConnection,
    SyncJob,
    WriteBackAudit,
    WriteBackRequest,
)
from backend.integrations.oracle_apex.repository import APEXRepository


class APEXService:
    """Oracle APEX integration service with circuit breaker and audit."""

    def __init__(
        self,
        *,
        repository: APEXRepository,
        adapter: OracleAPEXAdapter | None = None,
    ) -> None:
        self.repository = repository
        self.adapter = adapter

    def create_connection(
        self,
        endpoint: str,
        credentials_ref: str,
        *,
        tenant_id: str = "default",
        sync_schedule: str = "0 * * * *",
    ) -> OracleAPEXConnection:
        conn = OracleAPEXConnection(
            endpoint=endpoint,
            credentials_ref=credentials_ref,
            sync_schedule=sync_schedule,
        )
        # Store tenant_id in the payload for the repository
        conn.model_dump()["tenant_id"] = tenant_id
        self.repository.save_connection(conn)
        return conn

    def get_connection(self, connection_id: str) -> OracleAPEXConnection | None:
        return self.repository.get_connection(connection_id)

    def sync_data(
        self,
        connection_id: str,
        tenant_id: str,
        *,
        sample_data: list[dict[str, Any]] | None = None,
        crop: str = "unknown",
        region: str = "unknown",
    ) -> SyncJob:
        conn = self.repository.get_connection(connection_id)
        if conn is None:
            raise ValueError("Connection not found")

        job = SyncJob(connection_id=connection_id, tenant_id=tenant_id)

        if conn.circuit_breaker_state == CircuitBreakerState.OPEN:
            job.fail("Circuit breaker is OPEN")
            self.repository.save_sync_job(job)
            return job

        try:
            if self.adapter is not None:
                # Real data fetch via adapter
                records = self.adapter.fetch_data(conn.endpoint)
            else:
                # Fallback to simulated data (dev mode)
                records = sample_data or []

            ingested = len(records)
            validated = sum(1 for r in records if r.get("valid", True))
            quarantined = ingested - validated

            # Persist valid records as field records for the prediction pipeline
            for record in records:
                if record.get("valid", True):
                    features = {k: v for k, v in record.items() if k != "valid"}
                    checksum = hashlib.sha256(
                        json.dumps(features, sort_keys=True).encode()
                    ).hexdigest()[:16]
                    field_record = APEXFieldRecord(
                        record_id=str(uuid4()),
                        tenant_id=tenant_id,
                        crop=record.get("crop", crop),
                        region=record.get("region", region),
                        features=features,
                        checksum=checksum,
                        sync_job_id=job.job_id,
                    )
                    self.repository.save_field_record(field_record)

            conn.record_success()
            self.repository.save_connection(conn)
            job.complete(ingested, validated, quarantined)
        except Exception as exc:
            conn.record_failure()
            self.repository.save_connection(conn)
            job.fail(str(exc))

        self.repository.save_sync_job(job)
        return job

    def write_back(
        self,
        request: WriteBackRequest,
        *,
        tenant_id: str,
    ) -> WriteBackAudit:
        # Validate approval
        if not request.approved_by:
            raise ValueError("Write-back requires explicit operator approval")

        audit = WriteBackAudit(
            prediction_id=request.prediction_id,
            oracle_apex_table=request.oracle_apex_table,
            data_written=request.data_written,
            approved_by=request.approved_by,
            approved_at=request.approved_at,
        )

        try:
            if self.adapter is not None:
                # Real write-back via adapter
                self.adapter.write_data(
                    request.oracle_apex_table,
                    request.data_written,
                    request.approved_by,
                )
            # else: In dev mode without adapter, audit is recorded but no actual write

            audit.mark_completed()
        except Exception as exc:
            audit.mark_failed(str(exc))

        self.repository.save_writeback_audit(audit)
        return audit

    def get_circuit_state(self, connection_id: str) -> dict[str, Any]:
        conn = self.repository.get_connection(connection_id)
        if conn is None:
            raise ValueError("Connection not found")
        return {
            "connection_id": conn.connection_id,
            "state": conn.circuit_breaker_state.value,
            "failure_count": conn.failure_count,
            "last_failure_at": conn.last_failure_at.isoformat() if conn.last_failure_at else None,
        }

    def list_audits(self, tenant_id: str) -> list[WriteBackAudit]:
        return self.repository.list_writeback_audits(tenant_id)

    def health_check(self) -> bool:
        """Check Oracle APEX connectivity via adapter."""
        if self.adapter is None:
            return False
        return self.adapter.health_check()

    def get_latest_field_record(
        self, tenant_id: str, *, crop: str, region: str,
    ) -> APEXFieldRecord | None:
        """Look up the most recent field record for a tenant/crop/region."""
        return self.repository.get_latest_field_record(tenant_id, crop=crop, region=region)
