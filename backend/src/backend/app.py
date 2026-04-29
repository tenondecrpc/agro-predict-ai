from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .api_deprecations import ApiDeprecation
from .api_versioning import ApiVersioningConfig, install_api_versioning
from .billing import build_billing_router
from .compliance import build_data_retention_router
from .compliance.dpa_gate import DpaGateMiddleware
from .credentials import build_credential_rotation_router
from .data_ingestion.api import build_data_router
from .data_ingestion.service import IngestionService
from .integrations.oracle_apex.adapter import build_adapter_from_connection
from .integrations.oracle_apex.api import build_apex_router
from .integrations.oracle_apex.repository import PostgresAPEXRepository
from .integrations.oracle_apex.service import APEXService
from .knowledge import (
    InternalRagSettings,
    KnowledgeRepository,
    build_knowledge_router,
    probe_pgvector_extension,
)
from .llm.adapter import build_llm_adapter
from .llm.config import LLMConfig
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
from .procurement.agents.comparator import ComparatorAgent
from .procurement.agents.extractor import ExtractorAgent
from .procurement.agents.negotiator import NegotiatorAgent
from .procurement.agents.recommender import RecommenderAgent
from .procurement.api import build_procurement_router
from .procurement.decision_repository import (
    InMemoryDecisionRepository,
    PostgresDecisionRepository,
)
from .procurement.external.repository import (
    InMemoryExternalSignalRepository,
    PostgresExternalSignalRepository,
)
from .procurement.external.service import FXService, WeatherService
from .procurement.ml.supplier_predictor import SupplierPredictor
from .procurement.orchestrator import ProcurementOrchestrator
from .procurement.repository import (
    InMemoryProcurementRepository,
    PostgresProcurementRepository,
)
from .procurement.service import ProcurementService
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
    cors_origins = [
        origin.strip()
        for origin in os.getenv(
            "BACKEND_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:8080,http://127.0.0.1:8080",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
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
        if apex_service is None and adapters.database.configured:
            apex_service = APEXService(
                repository=PostgresAPEXRepository(
                    database_url=adapters.database.settings.sync_url(),
                ),
                adapter_factory=build_adapter_from_connection,
            )
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
        worker_status = _worker_health_snapshot(adapters)
        status = probe.status
        reasons = list(probe.reasons)
        if worker_status["queue_depth"] > worker_status["queue_depth_degraded_threshold"]:
            status = "degraded"
            reasons.append("worker_queue_backlog")
        response.status_code = 200 if status == "ok" else 503
        return {
            "status": status,
            "reasons": reasons,
            "worker": worker_status,
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

    # Procurement (spec 018) + external signals (spec 019 dependency)
    if adapters.database.configured:
        procurement_repo = PostgresProcurementRepository(
            database_url=adapters.database.settings.sync_url(),
        )
        external_repo = PostgresExternalSignalRepository(
            database_url=adapters.database.settings.sync_url(),
        )
        decision_repo = PostgresDecisionRepository(
            database_url=adapters.database.settings.sync_url(),
        )
    else:
        procurement_repo = InMemoryProcurementRepository()
        external_repo = InMemoryExternalSignalRepository()
        decision_repo = InMemoryDecisionRepository()
    procurement_service = ProcurementService(repository=procurement_repo)
    weather_service = WeatherService(repository=external_repo)
    fx_service = FXService(repository=external_repo)

    # LLM agents (spec 019 / 020). LLM_ENABLED=false produces deterministic
    # fallbacks so the demo always runs.
    llm_adapter = build_llm_adapter(LLMConfig.from_env())
    extractor_agent = ExtractorAgent(llm_adapter)
    comparator_agent = ComparatorAgent(llm_adapter)
    recommender_agent = RecommenderAgent(llm_adapter)
    negotiator_agent = NegotiatorAgent(llm_adapter)
    supplier_predictor = SupplierPredictor()
    orchestrator = ProcurementOrchestrator(
        domain_repo=procurement_repo,
        decision_repo=decision_repo,
        comparator=comparator_agent,
        recommender=recommender_agent,
        supplier_predictor=supplier_predictor,
        weather_service=weather_service,
        fx_service=fx_service,
    )

    app.include_router(
        build_procurement_router(
            procurement_service,
            weather_service=weather_service,
            fx_service=fx_service,
            extractor=extractor_agent,
            negotiator=negotiator_agent,
            orchestrator=orchestrator,
        )
    )
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


def _worker_health_snapshot(adapters: PersistenceAdapters) -> dict[str, int]:
    threshold = int(os.getenv("BACKEND_WORKER_QUEUE_DEPTH_DEGRADED_THRESHOLD", "100"))
    active_jobs = 0
    queue_depth = 0
    controller = adapters.worker_controller
    try:
        active_jobs = len(getattr(controller, "active_jobs", {}))
        if active_jobs == 0:
            active_jobs = len(getattr(controller, "_local_active_jobs", {}))
    except Exception:
        active_jobs = 0
    try:
        if hasattr(controller, "queued_jobs"):
            queue_depth = len(controller.queued_jobs())
    except Exception:
        queue_depth = 0
    return {
        "active_job_count": active_jobs,
        "queue_depth": queue_depth,
        "queue_depth_degraded_threshold": threshold,
    }


app = create_app()


def main() -> None:
    print("Use `uv run --project backend fastapi dev backend/src/backend/app.py` to start the API.")
