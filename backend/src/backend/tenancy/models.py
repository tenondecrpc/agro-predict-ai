from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class Tenant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    status: Literal["active", "suspended", "deleted"] = "active"
    resource_quotas: dict[str, int] = Field(default_factory=dict)
    budget_limit: float = 0.0
    budget_consumed: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def consume_budget(self, amount: float) -> None:
        self.budget_consumed += amount

    def has_budget(self, amount: float) -> bool:
        if self.budget_limit <= 0:
            return True
        return (self.budget_consumed + amount) <= self.budget_limit


class Team(BaseModel):
    model_config = ConfigDict(extra="forbid")

    team_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    name: str
    status: Literal["active", "suspended", "deleted"] = "active"
    resource_quotas: dict[str, int] = Field(default_factory=dict)
    budget_limit: float = 0.0
    budget_consumed: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def consume_budget(self, amount: float) -> None:
        self.budget_consumed += amount

    def has_budget(self, amount: float) -> bool:
        if self.budget_limit <= 0:
            return True
        return (self.budget_consumed + amount) <= self.budget_limit


class TenantContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    team_id: str
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    scope_level: Literal["tenant", "team"] = "team"


class QuotaTracker:
    """Simple in-memory quota tracker per team."""

    def __init__(self) -> None:
        self._counters: dict[str, dict[str, int]] = {}

    def check_and_consume(self, team_id: str, resource: str, limit: int) -> bool:
        key = f"{team_id}:{resource}"
        current = self._counters.get(key, 0)
        if current >= limit:
            return False
        self._counters[key] = current + 1
        return True

    def get_usage(self, team_id: str, resource: str) -> int:
        return self._counters.get(f"{team_id}:{resource}", 0)

    def reset(self, team_id: str, resource: str) -> None:
        self._counters.pop(f"{team_id}:{resource}", None)
