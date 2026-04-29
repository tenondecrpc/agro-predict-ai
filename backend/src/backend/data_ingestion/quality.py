from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.data_ingestion.models import DataRecord, GateType, QualityGateResult


class QualityGateEngine:
    """Evaluates data records against quality gates.

    Gates: completeness, freshness, range validity, cross-source consistency.
    """

    def evaluate_completeness(
        self,
        record: DataRecord,
        *,
        required_fields: list[str],
    ) -> QualityGateResult:
        missing = [f for f in required_fields if f not in record.data_payload]
        if missing:
            return QualityGateResult(
                gate_type=GateType.COMPLETENESS,
                passed=False,
                message=f"Missing required fields: {missing}",
                details={"missing_fields": missing},
            )
        return QualityGateResult(
            gate_type=GateType.COMPLETENESS,
            passed=True,
            message="All required fields present",
        )

    def evaluate_freshness(
        self,
        record: DataRecord,
        *,
        max_age_hours: float = 48.0,
        timestamp_field: str = "timestamp",
    ) -> QualityGateResult:
        raw = record.data_payload.get(timestamp_field)
        if raw is None:
            return QualityGateResult(
                gate_type=GateType.FRESHNESS,
                passed=False,
                message=f"Timestamp field '{timestamp_field}' missing",
                details={"timestamp_field": timestamp_field},
            )

        try:
            if isinstance(raw, str):
                ts = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            elif isinstance(raw, datetime):
                ts = raw
            else:
                raise ValueError("Unsupported timestamp type")
        except Exception as exc:
            return QualityGateResult(
                gate_type=GateType.FRESHNESS,
                passed=False,
                message=f"Invalid timestamp format: {exc}",
            )

        age = datetime.now(UTC) - ts
        if age > timedelta(hours=max_age_hours):
            return QualityGateResult(
                gate_type=GateType.FRESHNESS,
                passed=False,
                message=f"Data is stale: {age.total_seconds() / 3600:.1f} hours old",
                details={"age_hours": age.total_seconds() / 3600, "max_age_hours": max_age_hours},
            )

        return QualityGateResult(
            gate_type=GateType.FRESHNESS,
            passed=True,
            message="Data is fresh",
            details={"age_hours": age.total_seconds() / 3600},
        )

    def evaluate_range(
        self,
        record: DataRecord,
        *,
        field: str,
        min_val: float | int,
        max_val: float | int,
    ) -> QualityGateResult:
        value = record.data_payload.get(field)
        if value is None:
            return QualityGateResult(
                gate_type=GateType.RANGE,
                passed=False,
                message=f"Range check field '{field}' missing",
            )

        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return QualityGateResult(
                gate_type=GateType.RANGE,
                passed=False,
                message=f"Field '{field}' is not numeric: {value}",
            )

        if numeric < min_val or numeric > max_val:
            return QualityGateResult(
                gate_type=GateType.RANGE,
                passed=False,
                message=f"Field '{field}' value {numeric} outside range [{min_val}, {max_val}]",
                details={"field": field, "value": numeric, "min": min_val, "max": max_val},
            )

        return QualityGateResult(
            gate_type=GateType.RANGE,
            passed=True,
            message=f"Field '{field}' within range",
        )

    def evaluate_all(
        self,
        record: DataRecord,
        *,
        required_fields: list[str] | None = None,
        max_age_hours: float = 48.0,
        range_rules: dict[str, tuple[float | int, float | int]] | None = None,
    ) -> list[QualityGateResult]:
        results: list[QualityGateResult] = []

        if required_fields:
            results.append(self.evaluate_completeness(record, required_fields=required_fields))

        results.append(self.evaluate_freshness(record, max_age_hours=max_age_hours))

        if range_rules:
            for field, (min_val, max_val) in range_rules.items():
                results.append(self.evaluate_range(record, field=field, min_val=min_val, max_val=max_val))

        for result in results:
            record.add_quality_result(result)

        return results
