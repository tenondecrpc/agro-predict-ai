from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelStatus(StrEnum):
    REGISTERED = "registered"
    SHADOW = "shadow"
    ACTIVE = "active"
    ARCHIVED = "archived"


class ModelType(StrEnum):
    SKLEARN = "sklearn"
    XGBOOST = "xgboost"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"


class AccuracyMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    r2_score: float | None = None
    rmse: float | None = None
    mae: float | None = None
    accuracy: float | None = None
    validation_date: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ModelArtifact(BaseModel):
    artifact_id: str = Field(default_factory=lambda: str(uuid4()))
    model_id: str
    storage_path: str
    size_bytes: int = Field(..., ge=0)
    checksum: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_id: str = Field(default_factory=lambda: str(uuid4()))
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    model_type: ModelType
    tenant_id: str
    team_id: str
    training_date: datetime
    dataset_hash: str
    accuracy_metrics: AccuracyMetrics
    feature_schema: dict[str, str]
    status: ModelStatus = ModelStatus.REGISTERED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    activated_at: datetime | None = None

    def activate(self) -> None:
        self.status = ModelStatus.ACTIVE
        self.activated_at = datetime.now(UTC)

    def archive(self) -> None:
        self.status = ModelStatus.ARCHIVED

    def promote_to_shadow(self) -> None:
        self.status = ModelStatus.SHADOW


class ModelValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    validation_id: str = Field(default_factory=lambda: str(uuid4()))
    model_id: str
    shadow_model_id: str
    start_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    end_time: datetime | None = None
    prediction_count: int = 0
    accuracy_delta: float | None = None
    status: Literal["running", "completed", "failed"] = "running"
    comparison_results: dict[str, object] = Field(default_factory=dict)

    def complete(self, accuracy_delta: float, comparison: dict[str, object]) -> None:
        self.end_time = datetime.now(UTC)
        self.accuracy_delta = accuracy_delta
        self.comparison_results = comparison
        self.status = "completed" if accuracy_delta >= 0 else "failed"
