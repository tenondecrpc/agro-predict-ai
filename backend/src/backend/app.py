from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from .api_deprecations import ApiDeprecation
from .api_versioning import ApiVersioningConfig, install_api_versioning
from .billing import build_billing_router
from .compliance import build_data_retention_router
from .compliance.dpa_gate import DpaGateMiddleware
from .credentials import build_credential_rotation_router
from .data_ingestion.api import build_data_router
from .data_ingestion.service import IngestionService
from .integrations.oracle_apex.api import build_apex_router
from .integrations.oracle_apex.service import APEXService
from .knowledge import (
    InternalRagSettings,
    KnowledgeRepository,
    build_knowledge_router,
    probe_pgvector_extension,
)
from .ml_models.api import build_models_router
from .ml_models.repository import InMemoryModelRepository, PostgresModelRepository
from .ml_models.service import ModelService
from .operations.status_page import PublicStatusPage, PublicStatusPageService
from .persistence.factory import PersistenceAdapters, build_persistence_adapters
from .persistence.migrations import MigrationRunner
from .platform import build_platform_routers
from .predictions.api import build_predictions_router
from .predictions.field_data_resolver import FieldDataResolver
from .predictions.health_api import build_agent_health_router
from .predictions.service import PredictionService
from .runtime import ExecutionRequest, PlanningRequest, RuntimeWorkflow, TicketRunState
from .webhook import build_webhook_admin_router


class RuntimeSimulationRequest(BaseModel):
    planning: PlanningRequest
    execution: ExecutionRequest = Field(default_factory=ExecutionRequest)
    escalation_sinks: dict[str, str] | None = None


def create_app(
    workflow: RuntimeWorkflow | None = None,
    persistence: PersistenceAdapters | None = None,
    migration_runner: MigrationRunner | None = None,
    internal_rag_settings: InternalRagSettings | None = None,
    knowledge_repository: KnowledgeRepository | None = None,
    api_deprecations: tuple[ApiDeprecation, ...] = (),
    prediction_service: PredictionService | None = None,
    data_ingestion_service: IngestionService | None = None,
    model_service: ModelService | None = None,
    apex_service: APEXService | None = None,
    redis_client: Any = None,
) -> FastAPI:
    adapters = persistence or build_persistence_adapters()
    runner = migration_runner or MigrationRunner()
    rag_settings = internal_rag_settings or InternalRagSettings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        status = runner.ensure_current()
        app.state.persistence_migration_status = status
        adapters.health.update_migration_status(status)
        adapters.telemetry.set_gauge(
            "agropredict_persistence_migration_info",
            1.0,
            revision=status.current_revision or "none",
        )
        try:
            snapshot = adapters.control_plane_store.active_snapshot()
            adapters.health.update_active_snapshot_id(snapshot.snapshot_id)
        except Exception:
            adapters.health.update_active_snapshot_id(None)
        rag_probe = await probe_pgvector_extension(rag_settings)
        adapters.health.update_capability_probe(
            "internal_rag",
            ready=rag_probe.ready,
            reason=rag_probe.reason,
        )
        yield

    app = FastAPI(
        title="AgroPredict AI — Multi-Agent Predictive Intelligence Platform",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.persistence = adapters
    install_api_versioning(
        app,
        ApiVersioningConfig(
            deprecations=api_deprecations,
            telemetry=adapters.telemetry,
        ),
    )
    _checkpointer = None
    if adapters.checkpoint_saver is not None:
        _checkpointer = adapters.checkpoint_saver.build_saver()
    runtime_workflow = workflow or RuntimeWorkflow(
        repository=adapters.run_repository,
        checkpointer=_checkpointer,
        store=adapters.graph_store,
    )
    # Build agent execution repository for health endpoint and prediction service
    if adapters.database.configured:
        from backend.predictions.agent_execution_repository import PostgresAgentExecutionRepository

        agent_exec_repo = PostgresAgentExecutionRepository(
            database_url=adapters.database.settings.sync_url(),
        )
    else:
        from backend.predictions.agent_execution_repository import InMemoryAgentExecutionRepository

        agent_exec_repo = InMemoryAgentExecutionRepository()

    if prediction_service is None:
        prediction_repository = adapters.prediction_repository
        if prediction_repository is None:
            from .persistence.factory import build_prediction_repository

            prediction_repository = build_prediction_repository(adapters.database, adapters.redis)
        field_resolver = FieldDataResolver(apex_service) if apex_service is not None else None

        prediction_service = PredictionService(
            repository=prediction_repository,
            field_data_resolver=field_resolver,
            agent_exec_repository=agent_exec_repo,
        )

    system_router = APIRouter(tags=["system"])
    runtime_router = APIRouter(prefix="/api/v1/runtime", tags=["runtime"])
    status_router = APIRouter(prefix="/api/v1", tags=["status"])

    @system_router.get("/healthz")
    def healthz(response: Response) -> dict[str, object]:
        probe = adapters.health.liveness()
        response.status_code = 200 if probe.status == "ok" else 503
        return {
            "status": probe.status,
            "reasons": probe.reasons,
            "persistence": adapters.health.snapshot().model_dump(mode="json"),
        }

    @system_router.get("/readyz")
    def readyz(response: Response) -> dict[str, object]:
        probe = adapters.health.readiness()
        response.status_code = 200 if probe.status == "ok" else 503
        return {
            "status": probe.status,
            "reasons": probe.reasons,
            "persistence": adapters.health.snapshot().model_dump(mode="json"),
        }

    @system_router.get("/metrics")
    def metrics() -> Response:
        return Response(
            content=adapters.telemetry.render_prometheus(),
            media_type="text/plain; version=0.0.4",
        )

    @runtime_router.post("/simulate", response_model=TicketRunState)
    def simulate_run(request: RuntimeSimulationRequest) -> TicketRunState:
        try:
            return runtime_workflow.execute(
                planning_request=request.planning,
                execution_request=request.execution,
                escalation_sinks=request.escalation_sinks,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @status_router.get("/status-page", response_model=PublicStatusPage)
    def status_page() -> PublicStatusPage:
        return PublicStatusPageService(
            health=adapters.health,
            telemetry=adapters.telemetry,
        ).snapshot()

    app.include_router(system_router)
    app.include_router(runtime_router)
    app.include_router(status_router)
    app.include_router(build_predictions_router(prediction_service, redis_client=redis_client or adapters.redis))
    app.include_router(build_agent_health_router(repository=agent_exec_repo))
    if data_ingestion_service is not None:
        app.include_router(build_data_router(data_ingestion_service))
    if model_service is None:
        if adapters.database.configured:
            model_repo = PostgresModelRepository(
                database_url=adapters.database.settings.sync_url(),
            )
        else:
            model_repo = InMemoryModelRepository()
        model_service = ModelService(repository=model_repo)
    if model_service is not None:
        app.include_router(build_models_router(model_service))
    if apex_service is not None:
        app.include_router(build_apex_router(apex_service))
    for router in build_platform_routers(
        worker_controller=adapters.worker_controller,
        webhook_guard=adapters.webhook_guard,
        api_deprecations=api_deprecations,
        metering_ledger=adapters.metering_ledger,
    ):
        app.include_router(router)
    app.include_router(
        build_knowledge_router(
            repository=knowledge_repository,
            settings=rag_settings,
            telemetry=adapters.telemetry,
        )
    )
    from .supply_chain.admission import build_admission_router

    app.include_router(build_admission_router())
    app.include_router(
        build_billing_router(
            metering_ledger=adapters.metering_ledger,
        )
    )
    app.include_router(build_webhook_admin_router())
    if adapters.database.configured:
        app.include_router(
            build_credential_rotation_router(
                database_url=adapters.database.settings.sync_url(),
            )
        )
        app.include_router(
            build_data_retention_router(
                database_url=adapters.database.settings.sync_url(),
            )
        )
        app.add_middleware(
            DpaGateMiddleware,
            database_url=adapters.database.settings.sync_url(),
        )
    return app


app = create_app()


def main() -> None:
    print("Use `uv run --project backend fastapi dev backend/src/backend/app.py` to start the API.")
