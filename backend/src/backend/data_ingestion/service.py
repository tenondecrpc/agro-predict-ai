from __future__ import annotations

from time import perf_counter

from backend.data_ingestion.models import DataQualitySummary, DataRecord, DataSource, IngestionBatch, IngestionSummary
from backend.data_ingestion.quality import QualityGateEngine
from backend.data_ingestion.repository import DataRepository


class IngestionService:
    """Orchestrates data ingestion with validation and quality gates."""

    def __init__(
        self,
        *,
        repository: DataRepository,
        quality_engine: QualityGateEngine | None = None,
    ) -> None:
        self.repository = repository
        self.quality_engine = quality_engine or QualityGateEngine()

    def ingest_single(
        self,
        source_id: str,
        tenant_id: str,
        team_id: str,
        data_payload: dict[str, object],
        *,
        required_fields: list[str] | None = None,
        range_rules: dict[str, tuple[float | int, float | int]] | None = None,
    ) -> DataRecord:
        record = DataRecord(
            source_id=source_id,
            tenant_id=tenant_id,
            team_id=team_id,
            data_payload=data_payload,
        )
        self.quality_engine.evaluate_all(
            record,
            required_fields=required_fields,
            range_rules=range_rules,
        )
        self.repository.save_record(record)
        return record

    def ingest_batch(
        self,
        batch: IngestionBatch,
        *,
        required_fields: list[str] | None = None,
        range_rules: dict[str, tuple[float | int, float | int]] | None = None,
    ) -> IngestionSummary:
        start = perf_counter()
        provenance_ids: list[str] = []
        quarantined = 0
        errors = 0

        for payload in batch.records:
            try:
                record = self.ingest_single(
                    batch.source_id,
                    batch.tenant_id,
                    batch.team_id,
                    payload,
                    required_fields=required_fields,
                    range_rules=range_rules,
                )
                provenance_ids.append(record.provenance_id)
                if record.quality_status.value == "quarantined":
                    quarantined += 1
            except Exception:
                errors += 1

        duration_ms = int((perf_counter() - start) * 1000)
        return IngestionSummary(
            ingested=len(provenance_ids),
            quarantined=quarantined,
            errors=errors,
            provenance_ids=provenance_ids,
            duration_ms=duration_ms,
        )

    def get_record(self, record_id: str, *, tenant_id: str) -> DataRecord | None:
        return self.repository.get_record(record_id, tenant_id=tenant_id)

    def list_records(self, tenant_id: str) -> list[DataRecord]:
        return self.repository.list_records_by_tenant(tenant_id)

    def get_quality_summary(self, tenant_id: str) -> DataQualitySummary:
        return self.repository.get_quality_summary(tenant_id)

    def register_source(self, source: DataSource) -> DataSource:
        return self.repository.save_source(source)

    def get_source(self, source_id: str) -> DataSource | None:
        return self.repository.get_source(source_id)
