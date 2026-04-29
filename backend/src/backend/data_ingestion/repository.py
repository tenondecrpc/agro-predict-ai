from __future__ import annotations

from typing import Protocol, runtime_checkable

from backend.data_ingestion.models import DataQualitySummary, DataRecord, DataSource


@runtime_checkable
class DataRepository(Protocol):
    def save_record(self, record: DataRecord) -> DataRecord: ...

    def get_record(self, record_id: str, *, tenant_id: str) -> DataRecord | None: ...

    def list_records_by_tenant(self, tenant_id: str) -> list[DataRecord]: ...

    def save_source(self, source: DataSource) -> DataSource: ...

    def get_source(self, source_id: str) -> DataSource | None: ...

    def get_quality_summary(self, tenant_id: str) -> DataQualitySummary: ...


class InMemoryDataRepository:
    def __init__(self) -> None:
        self._records: dict[str, DataRecord] = {}
        self._sources: dict[str, DataSource] = {}

    def save_record(self, record: DataRecord) -> DataRecord:
        self._records[record.record_id] = record.model_copy(deep=True)
        return record

    def get_record(self, record_id: str, *, tenant_id: str) -> DataRecord | None:
        rec = self._records.get(record_id)
        if rec is None or rec.tenant_id != tenant_id:
            return None
        return rec.model_copy(deep=True)

    def list_records_by_tenant(self, tenant_id: str) -> list[DataRecord]:
        return [r.model_copy(deep=True) for r in self._records.values() if r.tenant_id == tenant_id]

    def save_source(self, source: DataSource) -> DataSource:
        self._sources[source.source_id] = source.model_copy(deep=True)
        return source

    def get_source(self, source_id: str) -> DataSource | None:
        src = self._sources.get(source_id)
        return src.model_copy(deep=True) if src else None

    def get_quality_summary(self, tenant_id: str) -> DataQualitySummary:
        records = [r for r in self._records.values() if r.tenant_id == tenant_id]
        passed = sum(1 for r in records if r.quality_status.value == "passed")
        warning = sum(1 for r in records if r.quality_status.value == "warning")
        quarantined = sum(1 for r in records if r.quality_status.value == "quarantined")

        gate_summaries: dict[str, dict[str, int]] = {}
        for r in records:
            for qr in r.quality_results:
                gt = qr.gate_type.value
                if gt not in gate_summaries:
                    gate_summaries[gt] = {"passed": 0, "failed": 0}
                if qr.passed:
                    gate_summaries[gt]["passed"] += 1
                else:
                    gate_summaries[gt]["failed"] += 1

        return DataQualitySummary(
            tenant_id=tenant_id,
            total_records=len(records),
            passed_count=passed,
            warning_count=warning,
            quarantined_count=quarantined,
            gate_summaries=gate_summaries,
            quarantine_size=quarantined,
        )
