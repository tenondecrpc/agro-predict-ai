from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeploymentProfile(StrEnum):
    CONNECTED = "connected"
    AIR_GAPPED = "air_gapped"


class HPAConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: str
    min_replicas: int = Field(..., ge=1)
    max_replicas: int = Field(..., ge=1)
    cpu_target_percentage: int = Field(default=70, ge=1, le=100)
    queue_depth_target: int | None = None
    scale_up_stabilization_seconds: int = 30
    scale_down_stabilization_seconds: int = 300

    @model_validator(mode="after")
    def validate_replicas(self) -> HPAConfig:
        if self.min_replicas > self.max_replicas:
            raise ValueError("min_replicas must be <= max_replicas")
        return self


class HealthProbe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: str
    probe_type: Literal["liveness", "readiness"]
    path: str
    initial_delay_seconds: int = 10
    period_seconds: int = 10
    timeout_seconds: int = 5
    failure_threshold: int = 3


class ResourceQuota(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component_name: str
    cpu_request: str = "100m"
    cpu_limit: str = "500m"
    memory_request: str = "256Mi"
    memory_limit: str = "512Mi"


class DeploymentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: DeploymentProfile
    namespace: str = "agropredict"
    hpa_configs: list[HPAConfig] = Field(default_factory=list)
    health_probes: list[HealthProbe] = Field(default_factory=list)
    resource_quotas: list[ResourceQuota] = Field(default_factory=list)
    external_services_enabled: bool = True
    local_model_cache_path: str = "/app/models"

    @model_validator(mode="after")
    def validate_air_gapped(self) -> DeploymentConfig:
        if self.profile == DeploymentProfile.AIR_GAPPED:
            self.external_services_enabled = False
        return self

    def is_air_gapped(self) -> bool:
        return self.profile == DeploymentProfile.AIR_GAPPED
