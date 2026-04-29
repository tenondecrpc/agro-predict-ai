"""Procurement REST API (spec 018).

All endpoints accept ``tenant_id`` (and ``team_id`` where relevant) as
query parameters in the MVP. A real deployment would derive them from
the authenticated principal; the existing platform follows the same
pattern (see ``backend.integrations.oracle_apex.api``).

Cross-tenant lookups return 404 (never 403) to avoid existence leaks.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.procurement.agents.extractor import ExtractorAgent
from backend.procurement.agents.negotiator import NegotiatorAgent
from backend.procurement.agents.schemas import (
    ExtractedQuotation,
    NegotiationMessage,
    Recommendation,
)
from backend.procurement.external.models import FXRate, WeatherSnapshot
from backend.procurement.external.service import FXService, WeatherService
from backend.procurement.external.weather import UnknownDepartmentError
from backend.procurement.models import (
    ProcurementAuditEvent,
    PurchaseRequest,
    PurchaseRequestCreate,
    PurchaseRequestStatus,
    Quotation,
    QuotationCreate,
    Supplier,
    SupplierCreate,
)
from backend.procurement.orchestrator import PipelineResult, ProcurementOrchestrator
from backend.procurement.service import ProcurementService


class ExtractRequest(BaseModel):
    raw_text: str = Field(..., min_length=1)
    request_id: str | None = None
    tenant_id: str


class NegotiateRequest(BaseModel):
    target_improvements: dict = Field(default_factory=dict)
    tone: str = "cordial"
    tenant_id: str


class RecommendResponse(BaseModel):
    status: str
    request_id: str
    escalation_reason: str | None = None
    recommendation: Recommendation | None = None
    recommendation_id: str | None = None
    weather_risk_score: float | None = None
    fx_rate_usd_pyg: float | None = None
    score_count: int = 0


def build_procurement_router(
    service: ProcurementService,
    *,
    weather_service: WeatherService | None = None,
    fx_service: FXService | None = None,
    extractor: ExtractorAgent | None = None,
    negotiator: NegotiatorAgent | None = None,
    orchestrator: ProcurementOrchestrator | None = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/procurement", tags=["procurement"])

    # Suppliers ---------------------------------------------------------
    @router.post("/suppliers", response_model=Supplier, status_code=201)
    def create_supplier(payload: SupplierCreate, actor: str = "system") -> Supplier:
        return service.create_supplier(payload, actor=actor)

    @router.get("/suppliers/{supplier_id}", response_model=Supplier)
    def get_supplier(supplier_id: str, tenant_id: str) -> Supplier:
        supplier = service.get_supplier(supplier_id, tenant_id=tenant_id)
        if supplier is None:
            raise HTTPException(status_code=404, detail="supplier_not_found")
        return supplier

    @router.get("/suppliers", response_model=list[Supplier])
    def list_suppliers(tenant_id: str) -> list[Supplier]:
        return service.list_suppliers(tenant_id=tenant_id)

    # Purchase requests -------------------------------------------------
    @router.post("/requests", response_model=PurchaseRequest, status_code=201)
    def create_request(payload: PurchaseRequestCreate, actor: str = "system") -> PurchaseRequest:
        try:
            return service.create_request(payload, actor=actor)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.get("/requests/{request_id}", response_model=PurchaseRequest)
    def get_request(request_id: str, tenant_id: str) -> PurchaseRequest:
        request = service.get_request(request_id, tenant_id=tenant_id)
        if request is None:
            raise HTTPException(status_code=404, detail="purchase_request_not_found")
        return request

    @router.get("/requests", response_model=list[PurchaseRequest])
    def list_requests(
        tenant_id: str,
        team_id: str | None = None,
        status: str | None = None,
    ) -> list[PurchaseRequest]:
        return service.list_requests(tenant_id=tenant_id, team_id=team_id, status=status)

    @router.post("/requests/{request_id}/transition", response_model=PurchaseRequest)
    def transition_request(
        request_id: str,
        tenant_id: str,
        new_status: PurchaseRequestStatus,
        actor: str = "system",
    ) -> PurchaseRequest:
        try:
            return service.transition_request(
                request_id,
                tenant_id=tenant_id,
                new_status=new_status,
                actor=actor,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    # Quotations --------------------------------------------------------
    @router.post("/quotations", response_model=Quotation, status_code=201)
    def upload_quotation(payload: QuotationCreate, actor: str = "system") -> Quotation:
        return service.upload_quotation(payload, actor=actor)

    @router.get("/quotations/{quotation_id}", response_model=Quotation)
    def get_quotation(quotation_id: str, tenant_id: str) -> Quotation:
        q = service.get_quotation(quotation_id, tenant_id=tenant_id)
        if q is None:
            raise HTTPException(status_code=404, detail="quotation_not_found")
        return q

    @router.get(
        "/requests/{request_id}/quotations",
        response_model=list[Quotation],
    )
    def list_quotations(
        request_id: str,
        tenant_id: str,
        only_validated: bool = Query(default=False),
    ) -> list[Quotation]:
        return service.list_quotations_for_request(
            request_id, tenant_id=tenant_id, only_validated=only_validated
        )

    # Audit -------------------------------------------------------------
    @router.get("/audit", response_model=list[ProcurementAuditEvent])
    def list_audit(
        tenant_id: str, entity_id: str | None = None
    ) -> list[ProcurementAuditEvent]:
        return service.list_audit_events(tenant_id=tenant_id, entity_id=entity_id)

    # External signals (Phase 2) ---------------------------------------
    if weather_service is not None:

        @router.get("/weather/risk", response_model=WeatherSnapshot)
        def weather_risk(
            department: str,
            horizon_days: int = Query(default=10, ge=1, le=16),
        ) -> WeatherSnapshot:
            try:
                return weather_service.get_or_fetch(
                    department=department, horizon_days=horizon_days
                )
            except UnknownDepartmentError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(status_code=503, detail=f"weather_provider_unavailable: {exc}") from exc

    if fx_service is not None:

        @router.get("/fx/usd_pyg", response_model=FXRate)
        def fx_usd_pyg() -> FXRate:
            return fx_service.get_or_fetch(base="USD", quote="PYG")

        @router.get("/fx/{base}/{quote}", response_model=FXRate)
        def fx_pair(base: str, quote: str) -> FXRate:
            return fx_service.get_or_fetch(base=base.upper(), quote=quote.upper())

    # Phase 4 + 5 agent endpoints --------------------------------------
    if extractor is not None:

        @router.post("/quotations/extract", response_model=ExtractedQuotation)
        def extract_quotation(payload: ExtractRequest) -> ExtractedQuotation:
            request: PurchaseRequest | None = None
            if payload.request_id:
                request = service.get_request(payload.request_id, tenant_id=payload.tenant_id)
            return extractor.extract(payload.raw_text, request=request)

    if orchestrator is not None:

        @router.post("/requests/{request_id}/recommend", response_model=RecommendResponse)
        def recommend_request(request_id: str, tenant_id: str) -> RecommendResponse:
            result: PipelineResult = orchestrator.recommend(request_id, tenant_id=tenant_id)
            if result.status == "escalated":
                # 422 = the request is well-formed but business rules
                # block recommendation (e.g. <2 validated quotations).
                raise HTTPException(
                    status_code=422,
                    detail={
                        "status": "escalated",
                        "escalation_reason": result.escalation_reason,
                    },
                )
            return RecommendResponse(
                status=result.status,
                request_id=result.request_id,
                escalation_reason=result.escalation_reason,
                recommendation=result.recommendation,
                recommendation_id=result.recommendation_id,
                weather_risk_score=(
                    float(result.weather_risk_score) if result.weather_risk_score is not None else None
                ),
                fx_rate_usd_pyg=(
                    float(result.fx_rate_usd_pyg) if result.fx_rate_usd_pyg is not None else None
                ),
                score_count=len(result.scores),
            )

    if negotiator is not None:

        @router.post(
            "/quotations/{quotation_id}/negotiate",
            response_model=NegotiationMessage,
        )
        def negotiate_quotation(
            quotation_id: str, payload: NegotiateRequest
        ) -> NegotiationMessage:
            quotation = service.get_quotation(quotation_id, tenant_id=payload.tenant_id)
            if quotation is None:
                raise HTTPException(status_code=404, detail="quotation_not_found")
            request = service.get_request(quotation.request_id, tenant_id=payload.tenant_id)
            if request is None:
                raise HTTPException(status_code=404, detail="purchase_request_not_found")
            supplier = service.get_supplier(quotation.supplier_id, tenant_id=payload.tenant_id)
            other_quotes = [
                q
                for q in service.list_quotations_for_request(
                    quotation.request_id, tenant_id=payload.tenant_id, only_validated=True
                )
                if q.quotation_id != quotation_id
            ]
            best_alternative = (
                min(other_quotes, key=lambda q: q.total_amount) if other_quotes else None
            )
            tone_value = payload.tone if payload.tone in {"cordial", "formal", "asertivo"} else "cordial"
            return negotiator.draft(
                quotation=quotation,
                supplier=supplier,
                request=request,
                best_alternative=best_alternative,
                target_improvements=payload.target_improvements,
                tone=tone_value,  # type: ignore[arg-type]
            )

    return router
