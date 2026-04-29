from __future__ import annotations

from datetime import UTC, datetime

from backend.predictions.models import PredictionInput


class DataQualityError(Exception):
    def __init__(
        self,
        message: str,
        *,
        uncertainty_flagged: bool = True,
        escalate: bool = False,
        missing_fields: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.uncertainty_flagged = uncertainty_flagged
        self.escalate = escalate
        self.missing_fields = missing_fields or []


class DataAnalystAgent:
    """Validates and analyzes input data before model execution.

    Enforces data quality gates:
    - Required fields per crop/region
    - Data freshness (flag stale > 48h)
    - Cross-source contradictions
    - Computes data provenance entries
    """

    # Crop-region required fields mapping
    REQUIRED_FIELDS: dict[str, dict[str, list[str]]] = {
        "corn": {
            "midwest_us": ["soil_moisture", "temperature_c", "rainfall_mm"],
            "default": ["soil_moisture", "temperature_c"],
        },
        "default": {
            "default": ["soil_moisture", "temperature_c"],
        },
    }

    # Freshness threshold in hours
    FRESHNESS_THRESHOLD_HOURS = 48

    def execute(self, input_data: PredictionInput) -> dict[str, object]:
        required = self._get_required_fields(input_data.crop, input_data.region)
        missing = [f for f in required if f not in input_data.input_data]

        if missing:
            raise DataQualityError(
                f"Missing required fields for {input_data.crop}/{input_data.region}: {missing}",
                uncertainty_flagged=True,
                escalate=False,
                missing_fields=missing,
            )

        # Check for contradictions
        contradiction = self._detect_contradiction(input_data.input_data)
        if contradiction:
            raise DataQualityError(
                f"Data contradiction detected: {contradiction}",
                uncertainty_flagged=True,
                escalate=True,
            )

        # Check freshness
        freshness_hours = input_data.input_data.get("data_freshness_hours", 0)
        is_stale = isinstance(freshness_hours, (int, float)) and freshness_hours > self.FRESHNESS_THRESHOLD_HOURS

        uncertainty_reasons: list[str] = []
        if is_stale:
            uncertainty_reasons.append("stale_data")

        # Build provenance entries
        provenance = self._build_provenance(input_data)

        return {
            "validated": True,
            "input_data_hash": input_data.input_data_hash,
            "data_sources": provenance,
            "uncertainty_flagged": bool(uncertainty_reasons),
            "uncertainty_reasons": uncertainty_reasons,
            "validated_at": datetime.now(UTC).isoformat(),
        }

    def _get_required_fields(self, crop: str, region: str) -> list[str]:
        crop_req = self.REQUIRED_FIELDS.get(crop, self.REQUIRED_FIELDS["default"])
        return crop_req.get(region, crop_req.get("default", []))

    def _detect_contradiction(self, data: dict[str, object]) -> str | None:
        # Detect known contradiction patterns
        if "soil_moisture" in data and "soil_moisture_secondary" in data:
            primary = data["soil_moisture"]
            secondary = data["soil_moisture_secondary"]
            if isinstance(primary, (int, float)) and isinstance(secondary, (int, float)):
                diff = abs(primary - secondary)
                if diff > 0.15:  # Significant divergence
                    return f"soil_moisture divergence: {primary} vs {secondary}"
        return None

    def _build_provenance(self, input_data: PredictionInput) -> list[dict[str, object]]:
        now = datetime.now(UTC)
        entries = []
        for key in input_data.input_data:
            if key in ("data_freshness_hours", "soil_moisture_secondary"):
                continue
            entries.append({
                "source_id": f"input_field:{key}",
                "ingested_at": now.isoformat(),
                "validation_status": "passed",
                "checksum": input_data.input_data_hash[:16],
            })
        return entries
