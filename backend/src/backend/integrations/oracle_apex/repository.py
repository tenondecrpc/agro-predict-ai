from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import Connection, Engine, create_engine, text

from backend.integrations.oracle_apex.models import APEXFieldRecord, OracleAPEXConnection, SyncJob, WriteBackAudit
from backend.persistence.db import tenant_guc_values


@runtime_checkable
class APEXRepository(Protocol):
    def save_connection(self, connection: OracleAPEXConnection) -> OracleAPEXConnection: ...

    def get_connection(self, connection_id: str, *, tenant_id: str | None = None) -> OracleAPEXConnection | None: ...

    def save_sync_job(self, job: SyncJob) -> SyncJob: ...

    def get_sync_job(self, job_id: str, *, tenant_id: str | None = None) -> SyncJob | None: ...

    def save_writeback_audit(self, audit: WriteBackAudit) -> WriteBackAudit: ...

    def get_writeback_audit(self, audit_id: str, *, tenant_id: str | None = None) -> WriteBackAudit | None: ...

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

    def get_connection(self, connection_id: str, *, tenant_id: str | None = None) -> OracleAPEXConnection | None:
        c = self._connections.get(connection_id)
        if c is not None and tenant_id is not None and c.tenant_id != tenant_id:
            return None
        return c.model_copy(deep=True) if c else None

    def save_sync_job(self, job: SyncJob) -> SyncJob:
        self._sync_jobs[job.job_id] = job.model_copy(deep=True)
        return job

    def get_sync_job(self, job_id: str, *, tenant_id: str | None = None) -> SyncJob | None:
        j = self._sync_jobs.get(job_id)
        if j is not None and tenant_id is not None and j.tenant_id != tenant_id:
            return None
        return j.model_copy(deep=True) if j else None

    def save_writeback_audit(self, audit: WriteBackAudit) -> WriteBackAudit:
        self._writeback_audits[audit.audit_id] = audit.model_copy(deep=True)
        return audit

    def get_writeback_audit(self, audit_id: str, *, tenant_id: str | None = None) -> WriteBackAudit | None:
        a = self._writeback_audits.get(audit_id)
        if a is not None and tenant_id is not None and a.tenant_id != tenant_id:
            return None
        return a.model_copy(deep=True) if a else None

    def list_writeback_audits(self, tenant_id: str) -> list[WriteBackAudit]:
        return [
            a.model_copy(deep=True)
            for a in self._writeback_audits.values()
            if a.tenant_id == tenant_id
        ]

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
        with self._scoped_transaction(connection.tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO apex_connections (
                        connection_id, tenant_id, endpoint, credentials_ref, sync_schedule,
                        status, circuit_breaker_state, failure_count, last_failure_at, payload
                    )
                    VALUES (
                        :connection_id, :tenant_id, :endpoint, :credentials_ref, :sync_schedule,
                        :status, :circuit_breaker_state, :failure_count, :last_failure_at, CAST(:payload AS JSONB)
                    )
                    ON CONFLICT (connection_id) DO UPDATE
                    SET endpoint = :endpoint,
                        credentials_ref = :credentials_ref,
                        sync_schedule = :sync_schedule,
                        status = :status,
                        circuit_breaker_state = :circuit_breaker_state,
                        failure_count = :failure_count,
                        last_failure_at = :last_failure_at,
                        payload = CAST(:payload AS JSONB),
                        updated_at = NOW()
                    """
                ),
                {
                    "connection_id": connection.connection_id,
                    "tenant_id": connection.tenant_id,
                    "endpoint": connection.endpoint,
                    "credentials_ref": connection.credentials_ref,
                    "sync_schedule": connection.sync_schedule,
                    "status": connection.status,
                    "circuit_breaker_state": connection.circuit_breaker_state.value,
                    "failure_count": connection.failure_count,
                    "last_failure_at": connection.last_failure_at,
                    "payload": _json_dumps(payload),
                },
            )
        return connection

    def get_connection(self, connection_id: str, *, tenant_id: str | None = None) -> OracleAPEXConnection | None:
        with self._scoped_connection(tenant_id) as conn:
            query = """
                    SELECT payload FROM apex_connections
                    WHERE connection_id = :id
                    """
            params = {"id": connection_id}
            if tenant_id is not None:
                query = """
                    SELECT payload FROM apex_connections
                    WHERE connection_id = :id
                      AND tenant_id = :tenant_id
                    """
                params["tenant_id"] = tenant_id
            row = conn.execute(
                text(query),
                params,
            ).mappings().fetchone()
        if row is None:
            return None
        return OracleAPEXConnection.model_validate(row["payload"])

    def save_sync_job(self, job: SyncJob) -> SyncJob:
        payload = job.model_dump(mode="json")
        with self._scoped_transaction(job.tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO apex_sync_jobs (
                        job_id, tenant_id, connection_id, start_time, end_time,
                        records_ingested, records_validated, records_quarantined,
                        status, error_message, payload
                    )
                    VALUES (
                        :job_id, :tenant_id, :connection_id, :start_time, :end_time,
                        :records_ingested, :records_validated, :records_quarantined,
                        :status, :error_message, CAST(:payload AS JSONB)
                    )
                    ON CONFLICT (job_id) DO UPDATE
                    SET end_time = :end_time,
                        records_ingested = :records_ingested,
                        records_validated = :records_validated,
                        records_quarantined = :records_quarantined,
                        status = :status,
                        error_message = :error_message,
                        payload = CAST(:payload AS JSONB)
                    """
                ),
                {
                    "job_id": job.job_id,
                    "tenant_id": job.tenant_id,
                    "connection_id": job.connection_id,
                    "start_time": job.start_time,
                    "end_time": job.end_time,
                    "records_ingested": job.records_ingested,
                    "records_validated": job.records_validated,
                    "records_quarantined": job.records_quarantined,
                    "status": job.status,
                    "error_message": job.error_message,
                    "payload": _json_dumps(payload),
                },
            )
        return job

    def get_sync_job(self, job_id: str, *, tenant_id: str | None = None) -> SyncJob | None:
        with self._scoped_connection(tenant_id) as conn:
            row = conn.execute(
                text("SELECT payload FROM apex_sync_jobs WHERE job_id = :id"),
                {"id": job_id},
            ).mappings().fetchone()
        if row is None:
            return None
        return SyncJob.model_validate(row["payload"])

    def save_writeback_audit(self, audit: WriteBackAudit) -> WriteBackAudit:
        payload = audit.model_dump(mode="json")
        with self._scoped_transaction(audit.tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO apex_writeback_audits (
                        audit_id, tenant_id, prediction_id, oracle_apex_table,
                        data_written, approved_by, approved_at, status, error_message,
                        created_at, payload
                    )
                    VALUES (
                        :audit_id, :tenant_id, :prediction_id, :oracle_apex_table,
                        CAST(:data_written AS JSONB), :approved_by, :approved_at,
                        :status, :error_message, :created_at, CAST(:payload AS JSONB)
                    )
                    ON CONFLICT (audit_id) DO UPDATE
                    SET status = :status,
                        error_message = :error_message,
                        payload = CAST(:payload AS JSONB)
                    """
                ),
                {
                    "audit_id": audit.audit_id,
                    "tenant_id": audit.tenant_id,
                    "prediction_id": audit.prediction_id,
                    "oracle_apex_table": audit.oracle_apex_table,
                    "data_written": _json_dumps(audit.data_written),
                    "approved_by": audit.approved_by,
                    "approved_at": audit.approved_at,
                    "status": audit.status,
                    "error_message": audit.error_message,
                    "created_at": audit.created_at,
                    "payload": _json_dumps(payload),
                },
            )
        return audit

    def get_writeback_audit(self, audit_id: str, *, tenant_id: str | None = None) -> WriteBackAudit | None:
        with self._scoped_connection(tenant_id) as conn:
            row = conn.execute(
                text("SELECT payload FROM apex_writeback_audits WHERE audit_id = :id"),
                {"id": audit_id},
            ).mappings().fetchone()
        if row is None:
            return None
        return WriteBackAudit.model_validate(row["payload"])

    def list_writeback_audits(self, tenant_id: str) -> list[WriteBackAudit]:
        with self._scoped_connection(tenant_id) as conn:
            rows = conn.execute(
                text(
                    "SELECT payload FROM apex_writeback_audits WHERE tenant_id = :tenant_id"
                ),
                {"tenant_id": tenant_id},
            ).mappings().fetchall()
        return [WriteBackAudit.model_validate(row["payload"]) for row in rows]

    def save_field_record(self, record: APEXFieldRecord) -> APEXFieldRecord:
        with self._scoped_transaction(record.tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO apex_field_records
                        (record_id, tenant_id, crop, region, features, checksum, ingested_at, sync_job_id)
                    VALUES
                        (
                            :record_id, :tenant_id, :crop, :region, CAST(:features AS JSONB),
                            :checksum, :ingested_at, :sync_job_id
                        )
                    ON CONFLICT (record_id) DO UPDATE
                    SET features = CAST(:features AS JSONB), ingested_at = :ingested_at
                    """
                ),
                {
                    "record_id": record.record_id,
                    "tenant_id": record.tenant_id,
                    "crop": record.crop,
                    "region": record.region,
                    "features": _json_dumps(record.features),
                    "checksum": record.checksum,
                    "ingested_at": record.ingested_at,
                    "sync_job_id": record.sync_job_id,
                },
            )
        return record

    def get_latest_field_record(
        self, tenant_id: str, *, crop: str, region: str,
    ) -> APEXFieldRecord | None:
        with self._scoped_connection(tenant_id) as conn:
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
            ).mappings().fetchone()
        if row is None:
            return None
        return APEXFieldRecord(
            record_id=row["record_id"],
            tenant_id=row["tenant_id"],
            crop=row["crop"],
            region=row["region"],
            features=row["features"],
            checksum=row["checksum"],
            ingested_at=row["ingested_at"],
            sync_job_id=row["sync_job_id"],
        )

    @contextmanager
    def _scoped_connection(self, tenant_id: str | None) -> Iterator[Connection]:
        with self._engine.connect() as connection:
            for key, value in tenant_guc_values(tenant_id=tenant_id or "*", team_id="*").items():
                connection.execute(
                    text("SELECT set_config(:key, :value, true)"),
                    {"key": key, "value": value},
                )
            yield connection

    @contextmanager
    def _scoped_transaction(self, tenant_id: str) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            for key, value in tenant_guc_values(tenant_id=tenant_id, team_id="*").items():
                connection.execute(
                    text("SELECT set_config(:key, :value, true)"),
                    {"key": key, "value": value},
                )
            yield connection


def _json_dumps(value: Any) -> str:
    import json

    return json.dumps(value, default=str)
