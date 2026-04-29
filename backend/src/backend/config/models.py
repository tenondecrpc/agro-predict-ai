from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ConfigEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    config_id: str = Field(default_factory=lambda: str(uuid4()))
    config_key: str
    config_value: str
    version: int = 1
    tenant_id: str
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    active: bool = True

    def update(self, new_value: str, changed_by: str) -> ConfigEntry:
        return ConfigEntry(
            config_key=self.config_key,
            config_value=new_value,
            version=self.version + 1,
            tenant_id=self.tenant_id,
            created_by=changed_by,
            active=True,
        )


class ConfigAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audit_id: str = Field(default_factory=lambda: str(uuid4()))
    config_id: str
    version: int
    action: Literal["create", "update", "rollback", "delete"]
    performed_by: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    details: dict[str, object] = Field(default_factory=dict)
