from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Secret(BaseModel):
    model_config = ConfigDict(extra="forbid")

    secret_id: str = Field(default_factory=lambda: str(uuid4()))
    vault_path: str
    secret_type: Literal["database", "api_key", "encryption_key", "oauth"]
    rotation_schedule_days: int = Field(default=90, ge=1)
    last_rotated_at: datetime | None = None
    status: Literal["active", "expired", "rotating"] = "active"
    tenant_id: str | None = None

    def needs_rotation(self) -> bool:
        if self.last_rotated_at is None:
            return True
        age = datetime.now(UTC) - self.last_rotated_at
        return age.days >= self.rotation_schedule_days


class EncryptedData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_id: str = Field(default_factory=lambda: str(uuid4()))
    encrypted_payload: str
    encrypted_dek: str
    kek_version: str
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class BreakGlassEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    requested_by: str
    approved_by_1: str | None = None
    approved_by_2: str | None = None
    action_taken: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: Literal["pending", "approved", "denied"] = "pending"

    def approve(self, approver: str) -> None:
        if self.approved_by_1 is None:
            self.approved_by_1 = approver
        elif self.approved_by_2 is None and approver != self.approved_by_1:
            self.approved_by_2 = approver
            self.status = "approved"

    def is_fully_approved(self) -> bool:
        return self.approved_by_1 is not None and self.approved_by_2 is not None
