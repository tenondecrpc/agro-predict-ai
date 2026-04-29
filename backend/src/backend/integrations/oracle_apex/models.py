from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CircuitBreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class OracleAPEXConnection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    connection_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = "default"
    endpoint: str
    credentials_ref: str
    sync_schedule: str = "0 * * * *"  # cron expression
    status: Literal["active", "inactive"] = "active"
    circuit_breaker_state: CircuitBreakerState = CircuitBreakerState.CLOSED
    failure_count: int = 0
    last_failure_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_at = datetime.now(UTC)
        if self.failure_count >= 5:
            self.circuit_breaker_state = CircuitBreakerState.OPEN

    def record_success(self) -> None:
        if self.circuit_breaker_state == CircuitBreakerState.HALF_OPEN:
            self.circuit_breaker_state = CircuitBreakerState.CLOSED
            self.failure_count = 0
        elif self.circuit_breaker_state == CircuitBreakerState.OPEN:
            self.circuit_breaker_state = CircuitBreakerState.HALF_OPEN


class SyncJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    connection_id: str
    tenant_id: str
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    records_ingested: int = 0
    records_validated: int = 0
    records_quarantined: int = 0
    status: Literal["running", "completed", "failed"] = "running"
    error_message: str | None = None

    def complete(self, ingested: int, validated: int, quarantined: int) -> None:
        self.end_time = datetime.now(UTC)
        self.records_ingested = ingested
        self.records_validated = validated
        self.records_quarantined = quarantined
        self.status = "completed"

    def fail(self, message: str) -> None:
        self.end_time = datetime.now(UTC)
        self.status = "failed"
        self.error_message = message


class WriteBackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_id: str
    oracle_apex_table: str
    data_written: dict[str, object]
    approved_by: str
    approved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WriteBackAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str = "default"
    prediction_id: str
    oracle_apex_table: str
    data_written: dict[str, object]
    approved_by: str
    approved_at: datetime
    status: Literal["pending", "completed", "failed"] = "pending"
    error_message: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def mark_completed(self) -> None:
        self.status = "completed"

    def mark_failed(self, message: str) -> None:
        self.status = "failed"
        self.error_message = message


class APEXFieldRecord(BaseModel):
    """A single field data record synced from Oracle APEX.

    Stored in PostgreSQL so the FieldDataResolver can look up the latest
    features for a given tenant/crop/region combination.
    """

    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    crop: str
    region: str
    features: dict[str, object] = Field(default_factory=dict)
    checksum: str = ""
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sync_job_id: str | None = None
