from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DataSourceType(StrEnum):
    SENSOR_NETWORK = "sensor_network"
    SATELLITE = "satellite"
    MANUAL_ENTRY = "manual_entry"
    WEATHER_API = "weather_api"


class DataSourceStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class QualityStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    QUARANTINED = "quarantined"


class GateType(StrEnum):
    COMPLETENESS = "completeness"
    FRESHNESS = "freshness"
    RANGE = "range"
    CONSISTENCY = "consistency"


class DataSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    source_type: DataSourceType
    schema_version: str = "v1"
    rate_limit_rps: int = Field(default=10, ge=1)
    status: DataSourceStatus = DataSourceStatus.ACTIVE
    tenant_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QualityGateResult(BaseModel):
    gate_type: GateType
    passed: bool
    message: str | None = None
    details: dict[str, object] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DataRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(default_factory=lambda: str(uuid4()))
    provenance_id: str = Field(default_factory=lambda: str(uuid4()))
    source_id: str
    tenant_id: str
    team_id: str
    data_payload: dict[str, object]
    schema_version: str = "v1"
    quality_status: QualityStatus = QualityStatus.PASSED
    quality_results: list[QualityGateResult] = Field(default_factory=list)
    validation_errors: list[str] = Field(default_factory=list)
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    data_hash: str = ""

    @model_validator(mode="after")
    def compute_hash(self) -> DataRecord:
        if not self.data_hash:
            payload_json = json.dumps(
                self.data_payload, sort_keys=True, default=str
            )
            canonical = (
                f"{self.source_id}:{self.tenant_id}:"
                f"{self.ingestion_timestamp.isoformat()}:{payload_json}"
            )
            self.data_hash = sha256(canonical.encode("utf-8")).hexdigest()
        return self

    def add_quality_result(self, result: QualityGateResult) -> None:
        self.quality_results.append(result)
        if not result.passed:
            self.quality_status = QualityStatus.QUARANTINED


class IngestionBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    tenant_id: str
    team_id: str
    records: list[dict[str, object]]
    schema_version: str = "v1"


class IngestionSummary(BaseModel):
    ingested: int
    quarantined: int
    errors: int
    provenance_ids: list[str]
    duration_ms: int


class DataQualitySummary(BaseModel):
    tenant_id: str
    total_records: int
    passed_count: int
    warning_count: int
    quarantined_count: int
    gate_summaries: dict[str, dict[str, int]]
    quarantine_size: int
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


