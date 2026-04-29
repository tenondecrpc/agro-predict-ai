from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ARQJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    request_payload: dict[str, object]
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    enqueued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    error_history: list[str] = Field(default_factory=list)

    def start(self) -> None:
        self.status = "running"
        self.started_at = datetime.now(UTC)

    def complete(self) -> None:
        self.status = "completed"
        self.completed_at = datetime.now(UTC)

    def fail(self, error: str) -> None:
        self.retry_count += 1
        self.error_history.append(error)
        if self.retry_count >= self.max_retries:
            self.status = "failed"
        else:
            self.status = "pending"

    def should_move_to_dlq(self) -> bool:
        return self.retry_count >= self.max_retries


class DeadLetterJob(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dlq_id: str = Field(default_factory=lambda: str(uuid4()))
    original_job_id: str
    failure_reason: str
    retry_history: list[str]
    original_payload: dict[str, object]
    enqueued_at: datetime
    status: Literal["pending", "retried", "discarded"] = "pending"
    moved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def retry(self) -> ARQJob:
        return ARQJob(
            tenant_id="",  # Will be set by service
            request_payload=self.original_payload,
        )

    def discard(self) -> None:
        self.status = "discarded"


class CircuitBreaker(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_name: str
    state: Literal["closed", "open", "half_open"] = "closed"
    failure_count: int = 0
    failure_threshold: int = 5
    last_failure_at: datetime | None = None
    opened_at: datetime | None = None

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_at = datetime.now(UTC)
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.opened_at = datetime.now(UTC)

    def record_success(self) -> None:
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
        elif self.state == "open":
            self.state = "half_open"

    def can_execute(self) -> bool:
        return self.state in ("closed", "half_open")
