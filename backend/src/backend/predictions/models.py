from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from typing import Literal, TypedDict
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PredictionStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    MODEL_EXECUTING = "model_executing"
    GENERATING_RECOMMENDATIONS = "generating_recommendations"
    EXPLAINING = "explaining"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    DEGRADED = "degraded"
    ESCALATED = "escalated"
    FAILED = "failed"


class DataProvenanceEntry(BaseModel):
    source_id: str
    ingested_at: datetime
    validation_status: Literal["passed", "failed", "stale", "missing"]
    checksum: str


class ExplanationArtifactModel(BaseModel):
    feature_scores: dict[str, float]
    data_sources_used: list[str]
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    uncertainty_factors: list[str]
    human_readable_summary: str


class PredictionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    team_id: str
    crop: str
    region: str
    time_horizon_days: int = Field(..., ge=1, le=365)
    input_data: dict[str, object]
    input_data_hash: str = Field(default="")

    @model_validator(mode="after")
    def compute_hash(self) -> PredictionInput:
        if not self.input_data_hash:
            canonical = json.dumps(self.input_data, sort_keys=True, default=str)
            self.input_data_hash = sha256(canonical.encode("utf-8")).hexdigest()
        return self


class PredictionOutput(BaseModel):
    prediction_id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    team_id: str = "unknown"
    model_version: str
    status: PredictionStatus
    output: dict[str, object]
    confidence_interval: dict[str, float] | None = None
    feature_importance: dict[str, float] | None = None
    data_provenance: list[DataProvenanceEntry]
    explanation_artifact: ExplanationArtifactModel | None = None
    degradation_flags: list[str] = Field(default_factory=list)
    escalation_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_confidence_interval(self) -> PredictionOutput:
        if self.confidence_interval is not None:
            lower = self.confidence_interval.get("lower")
            upper = self.confidence_interval.get("upper")
            if lower is not None and upper is not None and lower > upper:
                raise ValueError("confidence_interval.lower must be <= upper")
        return self

    def mark_completed(self) -> None:
        self.status = PredictionStatus.COMPLETED
        self.completed_at = datetime.now(UTC)

    def mark_degraded(self, flags: list[str]) -> None:
        self.status = PredictionStatus.DEGRADED
        self.degradation_flags.extend(flags)
        self.completed_at = datetime.now(UTC)

    def mark_escalated(self, reason: str) -> None:
        self.status = PredictionStatus.ESCALATED
        self.escalation_reason = reason
        self.completed_at = datetime.now(UTC)


class AgentExecutionRecord(BaseModel):
    record_id: str = Field(default_factory=lambda: str(uuid4()))
    prediction_id: str
    agent_name: Literal["data_analyst", "ml_executor", "recommendation_engine", "explainability", "reviewer"]
    input_state: dict[str, object]
    output_state: dict[str, object]
    duration_ms: int = Field(..., ge=0)
    status: Literal["success", "failure", "degraded", "timeout"]
    error_message: str | None = None


class PredictionState(TypedDict, total=False):
    # Legacy fields (kept for backward compatibility)
    input: PredictionInput
    output: PredictionOutput
    agent_executions: list[AgentExecutionRecord]
    error: str | None
    escalation_reason: str | None
    current_agent: str | None

    # Extended fields for LangGraph StateGraph execution (SPEC 013)
    tenant_id: str
    team_id: str
    crop: str
    region: str
    input_data: dict
    model_version: str

    # Data analyst outputs
    validated_data: dict
    quality_flags: list[str]
    data_provenance_raw: list[dict]

    # ML executor outputs
    ml_output: dict
    confidence_interval: dict
    feature_importance: dict

    # Recommendation engine outputs
    recommendation: str
    priority: str
    actions: list[str]

    # Explainability outputs
    explanation_artifact: dict

    # Reviewer outputs
    review_result: dict

    # Pipeline metadata
    thread_id: str
    agent_executions_raw: list[dict]
    degradation_flags: list[str]

