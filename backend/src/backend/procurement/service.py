"""Procurement service layer (spec 018).

Wraps the repository with audit emission and the data quality gate.
The API layer talks only to this service.
"""

from __future__ import annotations

import logging
from datetime import date

from backend.procurement.data_quality_gate import evaluate_quotation
from backend.procurement.models import (
    ProcurementAuditEvent,
    PurchaseRequest,
    PurchaseRequestCreate,
    PurchaseRequestStatus,
    Quotation,
    QuotationCreate,
    QuotationStatus,
    Supplier,
    SupplierCreate,
)
from backend.procurement.repository import ProcurementRepository

logger = logging.getLogger(__name__)


class ProcurementService:
    def __init__(self, repository: ProcurementRepository) -> None:
        self._repo = repository

    # Suppliers ---------------------------------------------------------
    def create_supplier(self, payload: SupplierCreate, *, actor: str) -> Supplier:
        supplier = Supplier(**payload.model_dump())
        self._repo.save_supplier(supplier)
        self._audit(
            tenant_id=supplier.tenant_id,
            team_id=None,
            actor=actor,
            action="procurement.supplier.created",
            entity_type="supplier",
            entity_id=supplier.supplier_id,
            payload_summary={
                "legal_name": supplier.legal_name,
                "ruc": supplier.ruc,
                "country": supplier.country,
            },
        )
        return supplier

    def get_supplier(self, supplier_id: str, *, tenant_id: str) -> Supplier | None:
        return self._repo.get_supplier(supplier_id, tenant_id=tenant_id)

    def list_suppliers(self, *, tenant_id: str) -> list[Supplier]:
        return self._repo.list_suppliers(tenant_id=tenant_id)

    # Purchase requests -------------------------------------------------
    def create_request(
        self, payload: PurchaseRequestCreate, *, actor: str
    ) -> PurchaseRequest:
        # Validate criteria weights sum
        payload.criteria_weights.validate_sum()
        if payload.target_delivery_date < date.today():
            raise ValueError("target_delivery_date must not be in the past")
        if payload.budget_cap is not None and payload.budget_cap < 0:
            raise ValueError("budget_cap must be non-negative")

        request = PurchaseRequest(**payload.model_dump())
        self._repo.save_request(request)
        self._audit(
            tenant_id=request.tenant_id,
            team_id=request.team_id,
            actor=actor,
            action="procurement.request.created",
            entity_type="purchase_request",
            entity_id=request.request_id,
            payload_summary={"title": request.title, "status": request.status.value},
        )
        return request

    def get_request(self, request_id: str, *, tenant_id: str) -> PurchaseRequest | None:
        return self._repo.get_request(request_id, tenant_id=tenant_id)

    def list_requests(
        self,
        *,
        tenant_id: str,
        team_id: str | None = None,
        status: str | None = None,
    ) -> list[PurchaseRequest]:
        return self._repo.list_requests(tenant_id=tenant_id, team_id=team_id, status=status)

    def transition_request(
        self,
        request_id: str,
        *,
        tenant_id: str,
        new_status: PurchaseRequestStatus,
        actor: str,
    ) -> PurchaseRequest:
        request = self._repo.get_request(request_id, tenant_id=tenant_id)
        if request is None:
            raise LookupError(f"purchase request {request_id} not found")
        if new_status == PurchaseRequestStatus.READY_FOR_REVIEW:
            quotes = self._repo.list_quotations_for_request(
                request_id, tenant_id=tenant_id, only_validated=True
            )
            if len(quotes) < 2:
                raise ValueError(
                    "transition to ready_for_review requires at least 2 validated quotations"
                )
        request.status = new_status
        self._repo.save_request(request)
        self._audit(
            tenant_id=request.tenant_id,
            team_id=request.team_id,
            actor=actor,
            action=f"procurement.request.transitioned.{new_status.value}",
            entity_type="purchase_request",
            entity_id=request.request_id,
            payload_summary={"new_status": new_status.value},
        )
        return request

    # Quotations --------------------------------------------------------
    def upload_quotation(
        self, payload: QuotationCreate, *, actor: str
    ) -> Quotation:
        quotation = Quotation(**payload.model_dump())
        request = self._repo.get_request(payload.request_id, tenant_id=payload.tenant_id)
        supplier = self._repo.get_supplier(payload.supplier_id, tenant_id=payload.tenant_id)

        flags = evaluate_quotation(quotation, request=request, supplier=supplier)
        quotation.quality_flags = flags
        quotation.status = QuotationStatus.QUARANTINED if flags else QuotationStatus.VALIDATED

        self._repo.save_quotation(quotation)
        self._audit(
            tenant_id=quotation.tenant_id,
            team_id=request.team_id if request is not None else None,
            actor=actor,
            action=(
                "procurement.quotation.quarantined"
                if quotation.status == QuotationStatus.QUARANTINED
                else "procurement.quotation.validated"
            ),
            entity_type="quotation",
            entity_id=quotation.quotation_id,
            payload_summary={
                "supplier_id": quotation.supplier_id,
                "request_id": quotation.request_id,
                "currency": quotation.currency,
                "total_amount": str(quotation.total_amount),
                "quality_flags": [f.code for f in flags],
            },
        )
        return quotation

    def get_quotation(self, quotation_id: str, *, tenant_id: str) -> Quotation | None:
        return self._repo.get_quotation(quotation_id, tenant_id=tenant_id)

    def list_quotations_for_request(
        self,
        request_id: str,
        *,
        tenant_id: str,
        only_validated: bool = False,
    ) -> list[Quotation]:
        return self._repo.list_quotations_for_request(
            request_id, tenant_id=tenant_id, only_validated=only_validated
        )

    # Audit -------------------------------------------------------------
    def list_audit_events(
        self, *, tenant_id: str, entity_id: str | None = None
    ) -> list[ProcurementAuditEvent]:
        return self._repo.list_audit_events(tenant_id=tenant_id, entity_id=entity_id)

    def _audit(
        self,
        *,
        tenant_id: str,
        team_id: str | None,
        actor: str,
        action: str,
        entity_type: str,
        entity_id: str,
        payload_summary: dict,
    ) -> None:
        event = ProcurementAuditEvent(
            tenant_id=tenant_id,
            team_id=team_id,
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_summary=payload_summary,
        )
        try:
            self._repo.save_audit_event(event)
        except Exception:  # noqa: BLE001 - audit must never break the main flow
            logger.exception("failed to persist procurement audit event %s", action)
