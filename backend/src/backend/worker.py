from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from time import time
from typing import Any

from backend.persistence.contracts import WorkerController
from backend.persistence.factory import PersistenceAdapters, build_persistence_adapters
from backend.persistence.redis import build_redis_client
from backend.platform.queue import QueuedJob
from backend.predictions.field_data_resolver import FieldDataResolver
from backend.predictions.graph import PredictionGraph
from backend.predictions.models import PredictionInput
from backend.predictions.repository import PredictionRepository

logger = logging.getLogger(__name__)

WORKER_JOB_TIMEOUT_ENV_KEY = "BACKEND_WORKER_JOB_TIMEOUT_SECONDS"
WORKER_ID_ENV_KEY = "BACKEND_WORKER_ID"


@dataclass(slots=True)
class WorkerBootstrap:
    worker_controller: WorkerController
    queue_name: str = "ticket-runs"


_worker_id: str = ""
_persistence: PersistenceAdapters | None = None


def _get_worker_id() -> str:
    global _worker_id
    if not _worker_id:
        _worker_id = os.getenv(WORKER_ID_ENV_KEY) or f"worker-{uuid.uuid4().hex[:8]}"
    return _worker_id


def _get_persistence() -> PersistenceAdapters:
    global _persistence
    if _persistence is None:
        _persistence = build_persistence_adapters()
    return _persistence


def _get_prediction_repository() -> PredictionRepository:
    persistence = _get_persistence()
    if persistence.prediction_repository is None:
        raise RuntimeError("Prediction repository is not configured")
    return persistence.prediction_repository


def _get_job_timeout() -> int:
    timeout = int(os.getenv(WORKER_JOB_TIMEOUT_ENV_KEY, "300"))
    if timeout <= 0:
        raise ValueError(f"{WORKER_JOB_TIMEOUT_ENV_KEY} must be a positive integer")
    return timeout


async def on_startup(ctx: dict[str, Any]) -> None:
    """ARQ startup hook: build persistence and register worker."""
    global _persistence
    _persistence = build_persistence_adapters()
    worker_id = _get_worker_id()
    ctx["worker_id"] = worker_id
    ctx["worker_bootstrap"] = build_worker_bootstrap(_persistence)
    logger.info("arq_worker_started", extra={"worker_id": worker_id})


async def on_shutdown(ctx: dict[str, Any]) -> None:
    """ARQ shutdown hook: drain worker gracefully."""
    import asyncio
    worker_id = _get_worker_id()
    persistence = _get_persistence()
    try:
        persistence.worker_controller.begin_drain(worker_id)
        logger.info("arq_worker_drain_started", extra={"worker_id": worker_id})
        await asyncio.sleep(0)
        logger.info("arq_worker_drain_completed", extra={"worker_id": worker_id})
    except Exception:
        logger.warning("arq_worker_drain_failed", extra={"worker_id": worker_id})


async def process_prediction_run(
    ctx: dict[str, Any],
    *,
    tenant_id: str,
    team_id: str,
    run_id: str,
    crop: str,
    region: str,
    time_horizon_days: int = 30,
    input_data: dict[str, object] | None = None,
    model_version: str = "default",
    retry_count: int = 0,
    checkpoint_ref: str | None = None,
) -> dict[str, object]:
    """ARQ job handler that executes the full prediction pipeline.

    Receives job kwargs from the webhook/enqueue side, builds a PredictionInput,
    executes the PredictionGraph, and stores the result.
    """
    worker_id = _get_worker_id()
    persistence = _get_persistence()
    repo = _get_prediction_repository()
    job_id = ctx.get("job_id", run_id)
    queue_name = str(ctx.get("queue_name") or getattr(persistence.worker_controller, "queue_name", "ticket-runs"))
    assigned = False

    logger.info(
        "prediction_run_started",
        extra={
            "worker_id": worker_id,
            "job_id": job_id,
            "tenant_id": tenant_id,
            "run_id": run_id,
            "retry_count": retry_count,
        },
    )

    try:
        persistence.worker_controller.assign(
            worker_id,
            QueuedJob(
                job_id=str(job_id),
                tenant_id=tenant_id,
                team_id=team_id,
                run_id=run_id,
                queue_name=queue_name,
                enqueued_at=int(time()),
                retry_count=retry_count,
                checkpoint_ref=checkpoint_ref,
            ),
        )
        assigned = True
    except Exception:
        logger.warning(
            "worker_controller_assign_failed",
            extra={"worker_id": worker_id, "job_id": job_id},
        )

    redis_client = None
    if persistence.redis.configured:
        try:
            redis_client = build_redis_client(persistence.redis.settings)
        except Exception:
            redis_client = None

    def _update_status(current_node: str, status: str = "running") -> None:
        if redis_client is None:
            return
        try:
            key = f"job:{run_id}"
            redis_client.hset(key, "status", status)
            redis_client.hset(key, "current_node", current_node)
            progress_map = {
                "data_analyst": "10",
                "ml_executor": "40",
                "recommendation_engine": "60",
                "explainability": "80",
                "reviewer": "95",
                "completed": "100",
            }
            redis_client.hset(key, "progress_pct", progress_map.get(current_node, "0"))
            redis_client.expire(key, 86400)  # Refresh TTL on every update
        except Exception:
            pass  # Status updates are best-effort

    try:
        # Resolve input data from APEX if not provided
        resolved_input_data = input_data
        if not input_data:
            try:
                apex_service = getattr(persistence, "apex_service", None)
                if apex_service is not None:
                    resolver = FieldDataResolver(apex_service)
                    resolved = resolver.resolve(
                        tenant_id=tenant_id,
                        crop=crop,
                        region=region,
                        manual_input=None,
                    )
                    resolved_input_data = dict(resolved.feature_dict)
            except Exception as exc:
                logger.warning(
                    "apex_resolver_failed_in_worker",
                    extra={"error": str(exc)},
                )
                # If no input data and APEX fails, proceed with empty dict
                # The graph will handle missing data

        # Build prediction input
        prediction_input = PredictionInput(
            tenant_id=tenant_id,
            team_id=team_id,
            crop=crop,
            region=region,
            time_horizon_days=time_horizon_days,
            input_data=resolved_input_data or {},
        )

        # Write initial running status
        _update_status("data_analyst", "running")

        # Execute the prediction graph
        graph = PredictionGraph()
        output = graph.execute(prediction_input, model_version=model_version)

        # Store result
        repo.save(output)

        # Mark job complete in Redis
        if redis_client is not None:
            try:
                key = f"job:{run_id}"
                redis_client.hset(key, "status", "completed")
                redis_client.hset(key, "current_node", "completed")
                redis_client.hset(key, "progress_pct", "100")
                redis_client.hset(key, "prediction_id", output.prediction_id)
                redis_client.expire(key, 86400)
            except Exception:
                pass

        # Release checkpoint
        if assigned:
            try:
                persistence.worker_controller.checkpoint_and_release(
                    worker_id,
                    checkpoint_ref or output.prediction_id,
                )
            except Exception:
                logger.warning(
                    "checkpoint_release_failed",
                    extra={"worker_id": worker_id, "job_id": job_id},
                )
        try:
            if redis_client is not None:
                redis_client.decr(f"tenant_concurrency:{tenant_id}")
        except Exception:
            pass

        logger.info(
            "prediction_run_completed",
            extra={
                "worker_id": worker_id,
                "job_id": job_id,
                "status": output.status.value,
                "prediction_id": output.prediction_id,
            },
        )

        return {
            "prediction_id": output.prediction_id,
            "status": output.status.value,
            "tenant_id": tenant_id,
            "run_id": run_id,
        }

    except Exception as exc:
        logger.error(
            "prediction_run_failed",
            extra={
                "worker_id": worker_id,
                "job_id": job_id,
                "error": str(exc),
                "retry_count": retry_count,
            },
        )

        # Write failure status to Redis
        if redis_client is not None:
            try:
                key = f"job:{run_id}"
                redis_client.hset(key, "status", "failed")
                redis_client.hset(key, "error_message", str(exc))
                redis_client.expire(key, 86400)
            except Exception:
                pass

        if assigned:
            try:
                persistence.worker_controller.capture_terminal_failure(worker_id, str(exc))
            except Exception:
                logger.warning(
                    "dlq_capture_failed",
                    extra={"worker_id": worker_id, "job_id": job_id},
                )

        # Decrement tenant concurrency counter
        try:
            if redis_client is not None:
                redis_client.decr(f"tenant_concurrency:{tenant_id}")
        except Exception:
            pass

        raise


def build_worker_bootstrap(
    persistence: PersistenceAdapters | None = None,
) -> WorkerBootstrap:
    adapters = persistence or build_persistence_adapters()
    return WorkerBootstrap(
        worker_controller=adapters.worker_controller,
        queue_name=getattr(adapters.worker_controller, "queue_name", "ticket-runs"),
    )


def process_metering_rollups(
    tenant_id: str,
    period_start_iso: str,
    period_end_iso: str,
    persistence: PersistenceAdapters | None = None,
) -> int:
    adapters = persistence or build_persistence_adapters()
    period_start = datetime.fromisoformat(period_start_iso)
    period_end = datetime.fromisoformat(period_end_iso)
    rollups = adapters.metering_ledger.build_hourly_rollups(
        tenant_id=tenant_id,
        period_start=period_start,
        period_end=period_end,
    )
    return len(rollups)


def process_encryption_key_rotation(
    envelopes: list[dict[str, str]],
    persistence: PersistenceAdapters | None = None,
) -> list[dict[str, str]]:
    adapters = persistence or build_persistence_adapters()
    report = adapters.encryption.rotate_stale_envelopes(envelopes)
    total = max(report.total_envelopes, 1)
    compliant = report.total_envelopes - report.due_before_rotation
    adapters.telemetry.set_gauge(
        "agropredict_encryption_rotation_sla_ratio",
        compliant / total,
    )
    adapters.telemetry.set_gauge(
        "agropredict_encryption_rotation_due_total",
        float(report.due_before_rotation),
    )
    return report.rotated_envelopes


async def process_knowledge_ingestion(ctx: dict[str, object], job_id: str) -> dict[str, object]:
    service = ctx.get("knowledge_ingestion_service")
    if service is None or not hasattr(service, "process_job"):
        raise RuntimeError("knowledge_ingestion_service_missing")
    job = service.process_job(job_id)
    return job.model_dump(mode="json")


class WorkerSettings:
    """ARQ worker settings for the AgroPredict AI prediction pipeline.

    Usage: arq backend.worker.WorkerSettings
    """

    from arq.connections import RedisSettings as ArqRedisSettings

    functions = (process_prediction_run, process_metering_rollups, process_knowledge_ingestion)
    on_startup = on_startup
    on_shutdown = on_shutdown
    redis_settings = ArqRedisSettings.from_dsn(os.getenv("BACKEND_REDIS_URL", "redis://localhost:6379/0"))
    max_jobs = int(os.getenv("BACKEND_WORKER_MAX_JOBS", "1"))
    job_timeout = _get_job_timeout()
    queue_name = os.getenv("BACKEND_WORKER_QUEUE_NAME", "ticket-runs")
