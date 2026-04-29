from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Response

from backend.predictions.job_status import JobStatus
from backend.predictions.models import PredictionInput, PredictionOutput
from backend.predictions.service import PredictionService

logger = logging.getLogger(__name__)

_JOB_STATUS_TTL_SECONDS = 86400  # 24 hours
_JOB_STATUS_PREFIX = "job:"


def build_predictions_router(service: PredictionService, redis_client: Any = None) -> APIRouter:
    """Build the predictions router.

    When redis_client is provided, POST returns 202 Accepted and enqueues via ARQ.
    The synchronous GET /{prediction_id} endpoint is always available for backward compat.
    """
    router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])

    # ------------------------------------------------------------------
    # POST - create prediction (async via ARQ when Redis available)
    # ------------------------------------------------------------------

    @router.post("", status_code=202)
    def create_prediction(input_data: PredictionInput, response: Response) -> dict:
        """Enqueue a prediction run.

        Returns 202 with run_id and status_url. The result is available via the
        status endpoint once the worker completes.
        When Redis is unavailable, falls back to synchronous execution.
        """
        run_id = str(uuid4())

        if redis_client is not None:
            # Check tenant concurrency limit
            concurrency_key = f"tenant_concurrency:{input_data.tenant_id}"
            try:
                in_flight = int(redis_client.get(concurrency_key) or 0)
            except Exception:
                in_flight = 0

            if in_flight >= 10:  # max 10 concurrent jobs per tenant
                raise HTTPException(
                    status_code=429,
                    detail="Tenant concurrency limit reached",
                    headers={"Retry-After": "5"},
                )

            # Enqueue the job
            try:
                initial_status = JobStatus(
                    run_id=run_id,
                    tenant_id=input_data.tenant_id,
                    status="queued",
                    started_at=datetime.now(UTC),
                )
                _write_job_status(redis_client, run_id, initial_status)

                # Enqueue via ARQ
                _enqueue_prediction(redis_client, run_id, input_data)

                # Increment tenant concurrency counter
                redis_client.incr(concurrency_key)

                return {
                    "run_id": run_id,
                    "status": "queued",
                    "status_url": f"/api/v1/predictions/{run_id}/status",
                }
            except Exception as exc:
                logger.error("arq_enqueue_failed", extra={"error": str(exc)})
                raise HTTPException(
                    status_code=503,
                    detail="Failed to enqueue prediction job.",
                ) from exc

        # Redis unavailable - return 503
        raise HTTPException(
            status_code=503,
            detail="Prediction queue unavailable. Please try again later.",
        )

    # ------------------------------------------------------------------
    # GET /{run_id}/status - poll job status
    # ------------------------------------------------------------------

    @router.get("/{run_id}/status")
    def get_prediction_status(
        run_id: str,
        tenant_id: str = Query(..., description="Tenant ID for scoping"),
    ) -> dict:
        """Poll the status of an async prediction run.

        Returns the current node and progress. When completed, also includes
        the full prediction output from PostgreSQL.
        """
        if redis_client is None:
            raise HTTPException(status_code=404, detail="Status tracking not available without Redis")

        try:
            status = _read_job_status(redis_client, run_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        if status is None:
            raise HTTPException(status_code=404, detail="Run not found")

        # Tenant isolation check
        if status.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Run not found")

        response_data = status.to_response_dict()

        # If completed, include the full prediction
        if status.status == "completed" and status.prediction_id:
            prediction = service.get_prediction(status.prediction_id, tenant_id=tenant_id)
            if prediction is not None:
                response_data["prediction"] = prediction.model_dump(mode="json")

        return response_data

    # ------------------------------------------------------------------
    # POST /{run_id}/retry - re-enqueue from DLQ
    # ------------------------------------------------------------------

    @router.post("/{run_id}/retry", status_code=202)
    def retry_prediction(
        run_id: str,
        tenant_id: str = Query(..., description="Tenant ID for scoping"),
    ) -> dict:
        """Re-enqueue a failed prediction from the dead letter queue."""
        if redis_client is None:
            raise HTTPException(status_code=503, detail="Queue not available")

        # Look up the dead letter record from PostgreSQL
        dlq_record = service.get_dead_letter_record(run_id, tenant_id=tenant_id)
        if dlq_record is None:
            raise HTTPException(status_code=404, detail="DLQ record not found for run_id")

        # Build a new PredictionInput from the stored payload
        payload = dlq_record.get("payload", {})
        new_input = PredictionInput(
            tenant_id=tenant_id,
            team_id=payload.get("team_id", ""),
            crop=payload.get("crop", "unknown"),
            region=payload.get("region", "unknown"),
            time_horizon_days=payload.get("time_horizon_days", 30),
            input_data=payload.get("input_data", {}),
        )

        new_run_id = str(uuid4())
        initial_status = JobStatus(
            run_id=new_run_id,
            tenant_id=tenant_id,
            status="queued",
            started_at=datetime.now(UTC),
        )
        _write_job_status(redis_client, new_run_id, initial_status)
        _enqueue_prediction(redis_client, new_run_id, new_input)
        redis_client.incr(f"tenant_concurrency:{tenant_id}")

        # Archive the original DLQ record
        service.archive_dead_letter_record(run_id, tenant_id=tenant_id)

        return {
            "run_id": new_run_id,
            "status": "queued",
            "status_url": f"/api/v1/predictions/{new_run_id}/status",
        }

    # ------------------------------------------------------------------
    # GET /{prediction_id} - backward compat synchronous fetch by prediction_id
    # ------------------------------------------------------------------

    @router.get("/{prediction_id}", response_model=PredictionOutput)
    def get_prediction(
        prediction_id: str,
        tenant_id: str = Query(..., description="Tenant ID for scoping"),
    ) -> PredictionOutput:
        # Skip status sub-path collisions
        if prediction_id == "status":
            raise HTTPException(status_code=404, detail="Not found")
        result = service.get_prediction(prediction_id, tenant_id=tenant_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Prediction not found")
        return result

    @router.get("", response_model=list[PredictionOutput])
    def list_predictions(
        tenant_id: str = Query(..., description="Tenant ID for scoping"),
        status: str | None = Query(None, description="Filter by status (e.g., failed)"),
    ) -> list[PredictionOutput]:
        if status == "failed":
            return service.list_failed_predictions(tenant_id)
        return service.list_predictions(tenant_id)

    return router


def _write_job_status(redis_client: Any, run_id: str, status: JobStatus) -> None:
    key = f"{_JOB_STATUS_PREFIX}{run_id}"
    hash_data = status.to_redis_hash()
    for field, value in hash_data.items():
        redis_client.hset(key, field, value)
    redis_client.expire(key, _JOB_STATUS_TTL_SECONDS)


def _read_job_status(redis_client: Any, run_id: str) -> JobStatus | None:
    key = f"{_JOB_STATUS_PREFIX}{run_id}"
    try:
        # Try hgetall first
        if hasattr(redis_client, "hgetall"):
            data = redis_client.hgetall(key)
        else:
            return None
    except Exception:
        return None

    if not data:
        return None

    # Convert bytes to str if necessary (real Redis client returns bytes)
    decoded: dict[str, str] = {}
    for k, v in data.items():
        dk = k.decode() if isinstance(k, bytes) else str(k)
        dv = v.decode() if isinstance(v, bytes) else str(v)
        decoded[dk] = dv

    return JobStatus.from_redis_hash(decoded)


def _enqueue_prediction(redis_client: Any, run_id: str, input_data: PredictionInput) -> None:
    """Enqueue a prediction job via ARQ.

    This is a best-effort fire-and-forget. The API returns 202 before the worker starts.
    """
    import asyncio

    from arq import create_pool
    from arq.connections import RedisSettings as ArqRedisSettings

    async def _do_enqueue() -> None:
        # Build ArqRedisSettings from the redis client's connection info
        redis_url = getattr(redis_client, "_url", None) or "redis://localhost:6379/0"
        pool = await create_pool(ArqRedisSettings.from_dsn(redis_url), default_queue_name="ticket-runs")
        try:
            await pool.enqueue_job(
                "process_prediction_run",
                _job_id=run_id,
                tenant_id=input_data.tenant_id,
                team_id=input_data.team_id,
                run_id=run_id,
                crop=input_data.crop,
                region=input_data.region,
                time_horizon_days=input_data.time_horizon_days,
                input_data=dict(input_data.input_data),
                model_version="v1.2.0",
            )
        finally:
            await pool.close(close_connection_pool=True)

    # Run in a new event loop if not in async context
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule but don't wait (fire and forget)
            asyncio.ensure_future(_do_enqueue())
        else:
            loop.run_until_complete(_do_enqueue())
    except RuntimeError:
        asyncio.run(_do_enqueue())
