from __future__ import annotations

import json
import logging
from typing import Protocol, runtime_checkable

from sqlalchemy import Engine, create_engine, text

from backend.integrations.oracle_apex.models import APEXFieldRecord, OracleAPEXConnection, SyncJob, WriteBackAudit


@runtime_checkable
class APEXRepository(Protocol):
    def save_connection(self, connection: OracleAPEXConnection) -> OracleAPEXConnection: ...

    def get_connection(self, connection_id: str) -> OracleAPEXConnection | None: ...

    def save_sync_job(self, job: SyncJob) -> SyncJob: ...

    def get_sync_job(self, job_id: str) -> SyncJob | None: ...

    def save_writeback_audit(self, audit: WriteBackAudit) -> WriteBackAudit: ...

    def get_writeback_audit(self, audit_id: str) -> WriteBackAudit | None: ...

    def list_writeback_audits(self, tenant_id: str) -> list[WriteBackAudit]: ...

    def save_field_record(self, record: APEXFieldRecord) -> APEXFieldRecord: ...

    def get_latest_field_record(
        self, tenant_id: str, *, crop: str, region: str,
    ) -> APEXFieldRecord | None: ...


class InMemoryAPEXRepository:
    def __init__(self) -> None:
        self._connections: dict[str, OracleAPEXConnection] = {}
        self._sync_jobs: dict[str, SyncJob] = {}
        self._writeback_audits: dict[str, WriteBackAudit] = {}
        self._field_records: list[APEXFieldRecord] = []

    def save_connection(self, connection: OracleAPEXConnection) -> OracleAPEXConnection:
        self._connections[connection.connection_id] = connection.model_copy(deep=True)
        return connection

    def get_connection(self, connection_id: str) -> OracleAPEXConnection | None:
        c = self._connections.get(connection_id)
        return c.model_copy(deep=True) if c else None

    def save_sync_job(self, job: SyncJob) -> SyncJob:
        self._sync_jobs[job.job_id] = job.model_copy(deep=True)
        return job

    def get_sync_job(self, job_id: str) -> SyncJob | None:
        j = self._sync_jobs.get(job_id)
        return j.model_copy(deep=True) if j else None

    def save_writeback_audit(self, audit: WriteBackAudit) -> WriteBackAudit:
        self._writeback_audits[audit.audit_id] = audit.model_copy(deep=True)
        return audit

    def get_writeback_audit(self, audit_id: str) -> WriteBackAudit | None:
        a = self._writeback_audits.get(audit_id)
        return a.model_copy(deep=True) if a else None

    def list_writeback_audits(self, tenant_id: str) -> list[WriteBackAudit]:
        return [a.model_copy(deep=True) for a in self._writeback_audits.values()]

    def save_field_record(self, record: APEXFieldRecord) -> APEXFieldRecord:
        self._field_records.append(record.model_copy(deep=True))
        return record

    def get_latest_field_record(
        self, tenant_id: str, *, crop: str, region: str,
    ) -> APEXFieldRecord | None:
        matching = [
            r for r in self._field_records
            if r.tenant_id == tenant_id and r.crop == crop and r.region == region
        ]
        if not matching:
            return None
        latest = max(matching, key=lambda r: r.ingested_at)
        return latest.model_copy(deep=True)


class PostgresAPEXRepository:
    """PostgreSQL-backed repository for Oracle APEX state.

    Stores connections, sync jobs, and write-back audits in PostgreSQL
    with tenant-scoped queries.
    """

    def __init__(
        self,
        database_url: str,
        *,
        engine: Engine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._engine = engine or create_engine(database_url, future=True, pool_pre_ping=True)
        self._logger = logger or logging.getLogger(__name__)

    def save_connection(self, connection: OracleAPEXConnection) -> OracleAPEXConnection:
        payload = connection.model_dump(mode="json")
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO apex_connections (connection_id, tenant_id, payload)
                    VALUES (:connection_id, :tenant_id, :payload)
                    ON CONFLICT (connection_id) DO UPDATE
                    SET payload = :payload, updated_at = NOW()
                    """
                ),
                {
                    "connection_id": connection.connection_id,
                    "tenant_id": payload.get("tenant_id", "default"),
                    "payload": json.dumps(payload),
                },
            )
        return connection

    def get_connection(self, connection_id: str) -> OracleAPEXConnection | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT payload FROM apex_connections WHERE connection_id = :id"),
                {"id": connection_id},
            ).fetchone()
        if row is None:
            return None
        return OracleAPEXConnection.model_validate(json.loads(row[0]))

    def save_sync_job(self, job: SyncJob) -> SyncJob:
        payload = job.model_dump(mode="json")
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO apex_sync_jobs (job_id, payload)
                    VALUES (:job_id, :payload)
                    ON CONFLICT (job_id) DO UPDATE
                    SET payload = :payload
                    """
                ),
                {"job_id": job.job_id, "payload": json.dumps(payload)},
            )
        return job

    def get_sync_job(self, job_id: str) -> SyncJob | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT payload FROM apex_sync_jobs WHERE job_id = :id"),
                {"id": job_id},
            ).fetchone()
        if row is None:
            return None
        return SyncJob.model_validate(json.loads(row[0]))

    def save_writeback_audit(self, audit: WriteBackAudit) -> WriteBackAudit:
        payload = audit.model_dump(mode="json")
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO apex_writeback_audits (audit_id, tenant_id, payload)
                    VALUES (:audit_id, :tenant_id, :payload)
                    ON CONFLICT (audit_id) DO UPDATE
                    SET payload = :payload
                    """
                ),
                {
                    "audit_id": audit.audit_id,
                    "tenant_id": audit.prediction_id,  # Use prediction_id as tenant proxy
                    "payload": json.dumps(payload),
                },
            )
        return audit

    def get_writeback_audit(self, audit_id: str) -> WriteBackAudit | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT payload FROM apex_writeback_audits WHERE audit_id = :id"),
                {"id": audit_id},
            ).fetchone()
        if row is None:
            return None
        return WriteBackAudit.model_validate(json.loads(row[0]))

    def list_writeback_audits(self, tenant_id: str) -> list[WriteBackAudit]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT payload FROM apex_writeback_audits WHERE tenant_id = :tenant_id"
                ),
                {"tenant_id": tenant_id},
            ).fetchall()
        return [WriteBackAudit.model_validate(json.loads(row[0])) for row in rows]

    def save_field_record(self, record: APEXFieldRecord) -> APEXFieldRecord:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO apex_field_records
                        (record_id, tenant_id, crop, region, features, checksum, ingested_at, sync_job_id)
                    VALUES
                        (:record_id, :tenant_id, :crop, :region, :features, :checksum, :ingested_at, :sync_job_id)
                    ON CONFLICT (record_id) DO UPDATE
                    SET features = :features, ingested_at = :ingested_at
                    """
                ),
                {
                    "record_id": record.record_id,
                    "tenant_id": record.tenant_id,
                    "crop": record.crop,
                    "region": record.region,
                    "features": json.dumps(record.features),
                    "checksum": record.checksum,
                    "ingested_at": record.ingested_at,
                    "sync_job_id": record.sync_job_id,
                },
            )
        return record

    def get_latest_field_record(
        self, tenant_id: str, *, crop: str, region: str,
    ) -> APEXFieldRecord | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    """
                    SELECT record_id, tenant_id, crop, region, features, checksum,
                           ingested_at, sync_job_id
                    FROM apex_field_records
                    WHERE tenant_id = :tenant_id
                      AND crop = :crop
                      AND region = :region
                    ORDER BY ingested_at DESC
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "crop": crop, "region": region},
            ).fetchone()
        if row is None:
            return None
        return APEXFieldRecord(
            record_id=row[0],
            tenant_id=row[1],
            crop=row[2],
            region=row[3],
            features=row[4] if isinstance(row[4], dict) else json.loads(row[4]),
            checksum=row[5],
            ingested_at=row[6],
            sync_job_id=row[7],
        )
