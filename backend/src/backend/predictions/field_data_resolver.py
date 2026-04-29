"""FieldDataResolver - bridges Oracle APEX data into the prediction pipeline.

Resolves input features for a prediction request from:
1. Manual input (always wins if provided)
2. Oracle APEX latest sync data for tenant/crop/region
3. Raises NoInputDataError if neither is available
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.integrations.oracle_apex.service import APEXService

logger = logging.getLogger(__name__)


class NoInputDataError(Exception):
    """Raised when no input data is available from any source."""


@dataclass
class ResolvedInputData:
    """The resolved feature set for a prediction request."""

    feature_dict: dict[str, float]
    provenance: list[dict]
    is_stale: bool
    stale_age_seconds: int
    source: str  # "apex" | "manual" | "hybrid"
    degradation_flags: list[str] = field(default_factory=list)


class FieldDataResolver:
    """Resolves prediction input features from APEX or manual input.

    Priority:
    1. manual_input (provided directly in the request)
    2. APEX latest record for tenant/crop/region
    3. NoInputDataError if nothing available

    Staleness check:
    - If APEX data age > freshness_window_seconds, trigger an on-demand sync with timeout.
    - If refresh fails or still stale, add 'apex_data_stale' degradation flag.
    """

    def __init__(
        self,
        apex_service: APEXService | None,
        freshness_window_seconds: int | None = None,
        sync_timeout_seconds: float | None = None,
    ) -> None:
        import os
        self._apex_service = apex_service
        self._freshness_window_seconds = freshness_window_seconds or int(
            os.getenv("APEX_FRESHNESS_WINDOW_SECONDS", "3600")
        )
        self._sync_timeout_seconds = sync_timeout_seconds or float(
            os.getenv("APEX_SYNC_TIMEOUT_SECONDS", "10")
        )

    def resolve(
        self,
        tenant_id: str,
        crop: str,
        region: str,
        manual_input: dict | None,
    ) -> ResolvedInputData:
        """Resolve input data for a prediction request.

        Parameters
        ----------
        tenant_id: Tenant identifier for APEX scoping.
        crop: Crop type for feature lookup.
        region: Region for feature lookup.
        manual_input: Caller-provided feature dict. If non-empty, used as-is.
        """
        if manual_input:
            return ResolvedInputData(
                feature_dict=self._coerce_floats(manual_input),
                provenance=[{
                    "source_id": "manual_input",
                    "ingested_at": datetime.now(UTC).isoformat(),
                    "validation_status": "passed",
                    "checksum": "",
                }],
                is_stale=False,
                stale_age_seconds=0,
                source="manual",
                degradation_flags=[],
            )

        if self._apex_service is None:
            raise NoInputDataError(
                "No manual input provided and APEX service is not configured."
            )

        # Attempt to fetch latest APEX record for this tenant/crop/region
        apex_record = self._fetch_latest_apex_record(tenant_id, crop, region)

        if apex_record is None:
            raise NoInputDataError(
                f"No APEX data available for tenant={tenant_id} crop={crop} region={region}"
            )

        age_seconds, is_stale = self._check_staleness(apex_record)
        degradation_flags: list[str] = []

        if is_stale:
            logger.info(
                "apex_data_stale_triggering_refresh",
                extra={"tenant_id": tenant_id, "crop": crop, "age_seconds": age_seconds},
            )
            # Check circuit breaker before sync attempt
            circuit_open = False
            try:
                adapter = getattr(self._apex_service, "_adapter", None)
                if adapter is not None:
                    circuit_open = getattr(adapter, "is_open", False)
            except Exception:
                pass

            if circuit_open:
                degradation_flags.append("apex_circuit_open")
            else:
                refreshed, timed_out = self._try_on_demand_sync(tenant_id, crop, region)
                if timed_out:
                    degradation_flags.append("apex_sync_timeout")
                if refreshed is not None:
                    apex_record = refreshed
                    age_seconds, is_stale = self._check_staleness(apex_record)

            if is_stale:
                degradation_flags.append("apex_data_stale")

        feature_dict = self._coerce_floats(apex_record.get("features", {}))
        provenance = [
            {
                "source_id": f"apex:{apex_record.get('record_id', 'unknown')}:{field_name}",
                "ingested_at": apex_record.get("ingested_at", datetime.now(UTC).isoformat()),
                "validation_status": "stale" if is_stale else "passed",
                "checksum": self._checksum_value(value),
            }
            for field_name, value in apex_record.get("features", {}).items()
        ]

        return ResolvedInputData(
            feature_dict=feature_dict,
            provenance=provenance,
            is_stale=is_stale,
            stale_age_seconds=age_seconds,
            source="apex",
            degradation_flags=degradation_flags,
        )

    def _fetch_latest_apex_record(
        self,
        tenant_id: str,
        crop: str,
        region: str,
    ) -> dict | None:
        """Fetch the most recent APEX field data record."""
        try:
            if self._apex_service is None:
                return None

            record = self._apex_service.get_latest_field_record(
                tenant_id, crop=crop, region=region,
            )
            if record is None:
                return None

            return {
                "record_id": record.record_id,
                "features": record.features,
                "ingested_at": record.ingested_at.isoformat(),
                "checksum": record.checksum,
            }
        except Exception as exc:
            logger.warning(
                "apex_field_lookup_failed",
                extra={"tenant_id": tenant_id, "error": str(exc)},
            )
            return None

    def _check_staleness(self, record: dict) -> tuple[int, bool]:
        """Return (age_seconds, is_stale) for the given record."""
        ingested_at_raw = record.get("ingested_at")
        if not ingested_at_raw:
            return 0, False
        try:
            if isinstance(ingested_at_raw, str):
                ingested_at = datetime.fromisoformat(ingested_at_raw)
            elif isinstance(ingested_at_raw, datetime):
                ingested_at = ingested_at_raw
            else:
                return 0, False
            if ingested_at.tzinfo is None:
                ingested_at = ingested_at.replace(tzinfo=UTC)
            age = int((datetime.now(UTC) - ingested_at).total_seconds())
            return age, age > self._freshness_window_seconds
        except Exception:
            return 0, False

    def _try_on_demand_sync(
        self,
        tenant_id: str,
        crop: str,
        region: str,
    ) -> tuple[dict | None, bool]:
        """Trigger an on-demand sync and return (refreshed_record, timed_out)."""
        try:
            if self._apex_service is None:
                return None, False

            repo = getattr(self._apex_service, "repository", None)
            if repo is None:
                return None, False

            connections = getattr(repo, "_connections", {})
            if not connections:
                return None, False

            conn_id = next(iter(connections.keys()))

            # Run sync with timeout
            sync_result = [None]
            sync_error = [None]

            def _do_sync():
                try:
                    sync_result[0] = self._apex_service.sync_data(
                        conn_id, tenant_id, crop=crop, region=region,
                    )
                except Exception as exc:
                    sync_error[0] = exc

            thread = __import__("threading").Thread(target=_do_sync, daemon=True)
            thread.start()
            thread.join(timeout=self._sync_timeout_seconds)

            if thread.is_alive():
                # Timed out
                return None, True

            if sync_error[0] is not None:
                logger.warning(
                    "apex_on_demand_sync_failed",
                    extra={"tenant_id": tenant_id, "error": str(sync_error[0])},
                )
                return None, False

            # Re-fetch after sync
            record = self._apex_service.get_latest_field_record(
                tenant_id, crop=crop, region=region,
            )
            if record is None:
                return None, False
            return {
                "record_id": record.record_id,
                "features": record.features,
                "ingested_at": record.ingested_at.isoformat(),
                "checksum": record.checksum,
            }, False
        except Exception as exc:
            logger.warning(
                "apex_on_demand_sync_failed",
                extra={"tenant_id": tenant_id, "error": str(exc)},
            )
        return None, False

    @staticmethod
    def _coerce_floats(data: dict) -> dict[str, float]:
        """Convert all values in a dict to float, skipping non-numeric."""
        result: dict[str, float] = {}
        for k, v in data.items():
            try:
                result[str(k)] = float(v)
            except (TypeError, ValueError):
                pass
        return result

    @staticmethod
    def _checksum_value(value: object) -> str:
        """SHA-256 of the raw value, first 16 hex chars."""
        import hashlib
        return hashlib.sha256(str(value).encode()).hexdigest()[:16]
