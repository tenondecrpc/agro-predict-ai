"""Procurement repository (spec 018).

Two implementations:

- ``InMemoryProcurementRepository`` for tests and air-gapped fallback.
- ``PostgresProcurementRepository`` for production use, with tenant- and
  team-scoped queries enforced through PostgreSQL Row Level Security and
  the ``app.tenant_id`` / ``app.team_id`` GUCs already used by the rest
  of the platform.

Cross-tenant queries return ``None`` (translated to HTTP 404 at the API
boundary, never 403 - the spec requires no existence leaks).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from sqlalchemy import Connection, Engine, create_engine, text

from backend.persistence.db import tenant_guc_values
from backend.procurement.models import (
    ProcurementAuditEvent,
    PurchaseRequest,
    Quotation,
    Supplier,
)


@runtime_checkable
class ProcurementRepository(Protocol):
    # Suppliers
    def save_supplier(self, supplier: Supplier) -> Supplier: ...
    def get_supplier(self, supplier_id: str, *, tenant_id: str) -> Supplier | None: ...
    def list_suppliers(self, *, tenant_id: str) -> list[Supplier]: ...

    # Purchase requests
    def save_request(self, request: PurchaseRequest) -> PurchaseRequest: ...
    def get_request(self, request_id: str, *, tenant_id: str) -> PurchaseRequest | None: ...
    def list_requests(
        self, *, tenant_id: str, team_id: str | None = None, status: str | None = None
    ) -> list[PurchaseRequest]: ...

    # Quotations
    def save_quotation(self, quotation: Quotation) -> Quotation: ...
    def get_quotation(self, quotation_id: str, *, tenant_id: str) -> Quotation | None: ...
    def list_quotations_for_request(
        self, request_id: str, *, tenant_id: str, only_validated: bool = False
    ) -> list[Quotation]: ...

    # Audit
    def save_audit_event(self, event: ProcurementAuditEvent) -> ProcurementAuditEvent: ...
    def list_audit_events(self, *, tenant_id: str, entity_id: str | None = None) -> list[ProcurementAuditEvent]: ...


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------


class InMemoryProcurementRepository:
    def __init__(self) -> None:
        self._suppliers: dict[str, Supplier] = {}
        self._requests: dict[str, PurchaseRequest] = {}
        self._quotations: dict[str, Quotation] = {}
        self._audits: list[ProcurementAuditEvent] = []

    # Suppliers ---------------------------------------------------------
    def save_supplier(self, supplier: Supplier) -> Supplier:
        self._suppliers[supplier.supplier_id] = supplier.model_copy(deep=True)
        return supplier

    def get_supplier(self, supplier_id: str, *, tenant_id: str) -> Supplier | None:
        s = self._suppliers.get(supplier_id)
        if s is None or s.tenant_id != tenant_id:
            return None
        return s.model_copy(deep=True)

    def list_suppliers(self, *, tenant_id: str) -> list[Supplier]:
        return [s.model_copy(deep=True) for s in self._suppliers.values() if s.tenant_id == tenant_id]

    # Purchase requests -------------------------------------------------
    def save_request(self, request: PurchaseRequest) -> PurchaseRequest:
        self._requests[request.request_id] = request.model_copy(deep=True)
        return request

    def get_request(self, request_id: str, *, tenant_id: str) -> PurchaseRequest | None:
        r = self._requests.get(request_id)
        if r is None or r.tenant_id != tenant_id:
            return None
        return r.model_copy(deep=True)

    def list_requests(
        self, *, tenant_id: str, team_id: str | None = None, status: str | None = None
    ) -> list[PurchaseRequest]:
        results = [r for r in self._requests.values() if r.tenant_id == tenant_id]
        if team_id is not None:
            results = [r for r in results if r.team_id == team_id]
        if status is not None:
            results = [r for r in results if r.status == status]
        return [r.model_copy(deep=True) for r in results]

    # Quotations --------------------------------------------------------
    def save_quotation(self, quotation: Quotation) -> Quotation:
        self._quotations[quotation.quotation_id] = quotation.model_copy(deep=True)
        return quotation

    def get_quotation(self, quotation_id: str, *, tenant_id: str) -> Quotation | None:
        q = self._quotations.get(quotation_id)
        if q is None or q.tenant_id != tenant_id:
            return None
        return q.model_copy(deep=True)

    def list_quotations_for_request(
        self, request_id: str, *, tenant_id: str, only_validated: bool = False
    ) -> list[Quotation]:
        results = [
            q
            for q in self._quotations.values()
            if q.tenant_id == tenant_id and q.request_id == request_id
        ]
        if only_validated:
            results = [q for q in results if q.status == "validated"]
        return [q.model_copy(deep=True) for q in results]

    # Audit -------------------------------------------------------------
    def save_audit_event(self, event: ProcurementAuditEvent) -> ProcurementAuditEvent:
        self._audits.append(event.model_copy(deep=True))
        return event

    def list_audit_events(
        self, *, tenant_id: str, entity_id: str | None = None
    ) -> list[ProcurementAuditEvent]:
        results = [e for e in self._audits if e.tenant_id == tenant_id]
        if entity_id is not None:
            results = [e for e in results if e.entity_id == entity_id]
        return [e.model_copy(deep=True) for e in results]


# ---------------------------------------------------------------------------
# Postgres implementation
# ---------------------------------------------------------------------------


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value) if not isinstance(value, Decimal) else value


class PostgresProcurementRepository:
    """Tenant-scoped procurement repository backed by PostgreSQL.

    Stores first-class queryable columns plus a denormalized JSONB
    ``metadata_json`` column on each entity that holds the full
    Pydantic representation (mirroring the pattern used by spec 006).
    Reads reconstruct the entity from the JSONB payload to avoid
    column drift.
    """

    def __init__(
        self,
        database_url: str,
        *,
        engine: Engine | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self._engine = engine or create_engine(database_url, future=True, pool_pre_ping=True)
        self._logger = logger or logging.getLogger(__name__)

    # Suppliers ---------------------------------------------------------
    def save_supplier(self, supplier: Supplier) -> Supplier:
        payload = supplier.model_dump(mode="json")
        with self._scoped_transaction(supplier.tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_suppliers (
                        supplier_id, tenant_id, ruc, legal_name, commercial_name,
                        contact_email, contact_phone, country, primary_categories,
                        primary_origin_countries, is_importer, senave_registered,
                        iso_certified, status, risk_tier, metadata_json
                    ) VALUES (
                        :supplier_id, :tenant_id, :ruc, :legal_name, :commercial_name,
                        :contact_email, :contact_phone, :country, :primary_categories,
                        :primary_origin_countries, :is_importer, :senave_registered,
                        :iso_certified, :status, :risk_tier, CAST(:metadata_json AS JSONB)
                    )
                    ON CONFLICT (supplier_id) DO UPDATE
                    SET legal_name = EXCLUDED.legal_name,
                        commercial_name = EXCLUDED.commercial_name,
                        contact_email = EXCLUDED.contact_email,
                        contact_phone = EXCLUDED.contact_phone,
                        primary_categories = EXCLUDED.primary_categories,
                        primary_origin_countries = EXCLUDED.primary_origin_countries,
                        is_importer = EXCLUDED.is_importer,
                        senave_registered = EXCLUDED.senave_registered,
                        iso_certified = EXCLUDED.iso_certified,
                        status = EXCLUDED.status,
                        risk_tier = EXCLUDED.risk_tier,
                        metadata_json = EXCLUDED.metadata_json,
                        updated_at = now()
                    """
                ),
                {
                    "supplier_id": supplier.supplier_id,
                    "tenant_id": supplier.tenant_id,
                    "ruc": supplier.ruc,
                    "legal_name": supplier.legal_name,
                    "commercial_name": supplier.commercial_name,
                    "contact_email": supplier.contact_email,
                    "contact_phone": supplier.contact_phone,
                    "country": supplier.country,
                    "primary_categories": supplier.primary_categories,
                    "primary_origin_countries": supplier.primary_origin_countries,
                    "is_importer": supplier.is_importer,
                    "senave_registered": supplier.senave_registered,
                    "iso_certified": supplier.iso_certified,
                    "status": supplier.status.value,
                    "risk_tier": supplier.risk_tier,
                    "metadata_json": _json_dumps(payload),
                },
            )
        return supplier

    def get_supplier(self, supplier_id: str, *, tenant_id: str) -> Supplier | None:
        with self._scoped_connection(tenant_id) as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT metadata_json FROM procurement_suppliers
                        WHERE supplier_id = :id AND tenant_id = :tenant_id
                        """
                    ),
                    {"id": supplier_id, "tenant_id": tenant_id},
                )
                .mappings()
                .fetchone()
            )
        if row is None:
            return None
        return Supplier.model_validate(row["metadata_json"])

    def list_suppliers(self, *, tenant_id: str) -> list[Supplier]:
        with self._scoped_connection(tenant_id) as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT metadata_json FROM procurement_suppliers "
                        "WHERE tenant_id = :tenant_id ORDER BY legal_name"
                    ),
                    {"tenant_id": tenant_id},
                )
                .mappings()
                .fetchall()
            )
        return [Supplier.model_validate(r["metadata_json"]) for r in rows]

    # Purchase requests -------------------------------------------------
    def save_request(self, request: PurchaseRequest) -> PurchaseRequest:
        payload = request.model_dump(mode="json")
        with self._scoped_transaction(request.tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_purchase_requests (
                        request_id, tenant_id, team_id, requested_by, title, description,
                        category, urgency, currency, budget_cap, criteria_weights,
                        target_delivery_date, target_crop, target_zafra, fenological_window,
                        target_hectares, delivery_department, delivery_location,
                        current_stock_days, status, approver_id, approved_at,
                        awarded_quotation_id, metadata_json
                    ) VALUES (
                        :request_id, :tenant_id, :team_id, :requested_by, :title, :description,
                        :category, :urgency, :currency, :budget_cap, CAST(:criteria_weights AS JSONB),
                        :target_delivery_date, :target_crop, :target_zafra, :fenological_window,
                        :target_hectares, :delivery_department, :delivery_location,
                        :current_stock_days, :status, :approver_id, :approved_at,
                        :awarded_quotation_id, CAST(:metadata_json AS JSONB)
                    )
                    ON CONFLICT (request_id) DO UPDATE
                    SET title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        urgency = EXCLUDED.urgency,
                        currency = EXCLUDED.currency,
                        budget_cap = EXCLUDED.budget_cap,
                        criteria_weights = EXCLUDED.criteria_weights,
                        target_delivery_date = EXCLUDED.target_delivery_date,
                        status = EXCLUDED.status,
                        approver_id = EXCLUDED.approver_id,
                        approved_at = EXCLUDED.approved_at,
                        awarded_quotation_id = EXCLUDED.awarded_quotation_id,
                        metadata_json = EXCLUDED.metadata_json,
                        updated_at = now()
                    """
                ),
                {
                    "request_id": request.request_id,
                    "tenant_id": request.tenant_id,
                    "team_id": request.team_id,
                    "requested_by": request.requested_by,
                    "title": request.title,
                    "description": request.description,
                    "category": request.category,
                    "urgency": request.urgency.value,
                    "currency": request.currency,
                    "budget_cap": request.budget_cap,
                    "criteria_weights": _json_dumps(request.criteria_weights.model_dump()),
                    "target_delivery_date": request.target_delivery_date,
                    "target_crop": request.target_crop,
                    "target_zafra": request.target_zafra,
                    "fenological_window": request.fenological_window,
                    "target_hectares": request.target_hectares,
                    "delivery_department": request.delivery_department,
                    "delivery_location": request.delivery_location,
                    "current_stock_days": request.current_stock_days,
                    "status": request.status.value,
                    "approver_id": request.approver_id,
                    "approved_at": request.approved_at,
                    "awarded_quotation_id": request.awarded_quotation_id,
                    "metadata_json": _json_dumps(payload),
                },
            )
            # Replace items
            conn.execute(
                text("DELETE FROM procurement_request_items WHERE request_id = :rid"),
                {"rid": request.request_id},
            )
            for position, item in enumerate(request.items):
                conn.execute(
                    text(
                        """
                        INSERT INTO procurement_request_items (
                            item_id, request_id, tenant_id, description, quantity, unit,
                            specifications, target_unit_price, position
                        ) VALUES (
                            :item_id, :request_id, :tenant_id, :description, :quantity, :unit,
                            :specifications, :target_unit_price, :position
                        )
                        """
                    ),
                    {
                        "item_id": item.item_id,
                        "request_id": request.request_id,
                        "tenant_id": request.tenant_id,
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit": item.unit,
                        "specifications": item.specifications,
                        "target_unit_price": item.target_unit_price,
                        "position": position,
                    },
                )
        return request

    def get_request(self, request_id: str, *, tenant_id: str) -> PurchaseRequest | None:
        with self._scoped_connection(tenant_id) as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT metadata_json FROM procurement_purchase_requests
                        WHERE request_id = :id AND tenant_id = :tenant_id
                        """
                    ),
                    {"id": request_id, "tenant_id": tenant_id},
                )
                .mappings()
                .fetchone()
            )
        if row is None:
            return None
        return PurchaseRequest.model_validate(row["metadata_json"])

    def list_requests(
        self, *, tenant_id: str, team_id: str | None = None, status: str | None = None
    ) -> list[PurchaseRequest]:
        clauses = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": tenant_id}
        if team_id is not None:
            clauses.append("team_id = :team_id")
            params["team_id"] = team_id
        if status is not None:
            clauses.append("status = :status")
            params["status"] = status
        where = " AND ".join(clauses)
        with self._scoped_connection(tenant_id) as conn:
            rows = (
                conn.execute(
                    text(
                        f"SELECT metadata_json FROM procurement_purchase_requests "
                        f"WHERE {where} ORDER BY created_at DESC"
                    ),
                    params,
                )
                .mappings()
                .fetchall()
            )
        return [PurchaseRequest.model_validate(r["metadata_json"]) for r in rows]

    # Quotations --------------------------------------------------------
    def save_quotation(self, quotation: Quotation) -> Quotation:
        payload = quotation.model_dump(mode="json")
        with self._scoped_transaction(quotation.tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_quotations (
                        quotation_id, tenant_id, request_id, supplier_id, created_by,
                        currency, exchange_rate_quoted, incoterm, includes_iva, iva_rate,
                        payment_terms, total_amount, total_pyg_normalized, lead_time_days,
                        validity_until, warranty_months, discount_pct, terms_text,
                        attachment_ref, raw_extracted_text, extraction_confidence,
                        anomaly_score, anomaly_reason, status, quality_flags, metadata_json
                    ) VALUES (
                        :quotation_id, :tenant_id, :request_id, :supplier_id, :created_by,
                        :currency, :exchange_rate_quoted, :incoterm, :includes_iva, :iva_rate,
                        :payment_terms, :total_amount, :total_pyg_normalized, :lead_time_days,
                        :validity_until, :warranty_months, :discount_pct, :terms_text,
                        :attachment_ref, :raw_extracted_text, :extraction_confidence,
                        :anomaly_score, :anomaly_reason, :status, CAST(:quality_flags AS JSONB),
                        CAST(:metadata_json AS JSONB)
                    )
                    ON CONFLICT (quotation_id) DO UPDATE
                    SET status = EXCLUDED.status,
                        quality_flags = EXCLUDED.quality_flags,
                        anomaly_score = EXCLUDED.anomaly_score,
                        anomaly_reason = EXCLUDED.anomaly_reason,
                        metadata_json = EXCLUDED.metadata_json,
                        updated_at = now()
                    """
                ),
                {
                    "quotation_id": quotation.quotation_id,
                    "tenant_id": quotation.tenant_id,
                    "request_id": quotation.request_id,
                    "supplier_id": quotation.supplier_id,
                    "created_by": quotation.created_by,
                    "currency": quotation.currency,
                    "exchange_rate_quoted": quotation.exchange_rate_quoted,
                    "incoterm": quotation.incoterm,
                    "includes_iva": quotation.includes_iva,
                    "iva_rate": quotation.iva_rate,
                    "payment_terms": quotation.payment_terms,
                    "total_amount": quotation.total_amount,
                    "total_pyg_normalized": quotation.total_pyg_normalized,
                    "lead_time_days": quotation.lead_time_days,
                    "validity_until": quotation.validity_until,
                    "warranty_months": quotation.warranty_months,
                    "discount_pct": quotation.discount_pct,
                    "terms_text": quotation.terms_text,
                    "attachment_ref": quotation.attachment_ref,
                    "raw_extracted_text": quotation.raw_extracted_text,
                    "extraction_confidence": quotation.extraction_confidence,
                    "anomaly_score": quotation.anomaly_score,
                    "anomaly_reason": quotation.anomaly_reason,
                    "status": quotation.status.value,
                    "quality_flags": _json_dumps([f.model_dump() for f in quotation.quality_flags]),
                    "metadata_json": _json_dumps(payload),
                },
            )
            conn.execute(
                text("DELETE FROM procurement_quotation_items WHERE quotation_id = :qid"),
                {"qid": quotation.quotation_id},
            )
            for item in quotation.items:
                conn.execute(
                    text(
                        """
                        INSERT INTO procurement_quotation_items (
                            item_id, quotation_id, request_item_id, tenant_id, description,
                            quantity, unit_price, subtotal, brand, model, origin,
                            presentation, lead_time_days, notes
                        ) VALUES (
                            :item_id, :quotation_id, :request_item_id, :tenant_id, :description,
                            :quantity, :unit_price, :subtotal, :brand, :model, :origin,
                            :presentation, :lead_time_days, :notes
                        )
                        """
                    ),
                    {
                        "item_id": item.item_id,
                        "quotation_id": quotation.quotation_id,
                        "request_item_id": item.request_item_id,
                        "tenant_id": quotation.tenant_id,
                        "description": item.description,
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "subtotal": item.subtotal,
                        "brand": item.brand,
                        "model": item.model,
                        "origin": item.origin,
                        "presentation": item.presentation,
                        "lead_time_days": item.lead_time_days,
                        "notes": item.notes,
                    },
                )
        return quotation

    def get_quotation(self, quotation_id: str, *, tenant_id: str) -> Quotation | None:
        with self._scoped_connection(tenant_id) as conn:
            row = (
                conn.execute(
                    text(
                        """
                        SELECT metadata_json FROM procurement_quotations
                        WHERE quotation_id = :id AND tenant_id = :tenant_id
                        """
                    ),
                    {"id": quotation_id, "tenant_id": tenant_id},
                )
                .mappings()
                .fetchone()
            )
        if row is None:
            return None
        return Quotation.model_validate(row["metadata_json"])

    def list_quotations_for_request(
        self, request_id: str, *, tenant_id: str, only_validated: bool = False
    ) -> list[Quotation]:
        clauses = ["tenant_id = :tenant_id", "request_id = :request_id"]
        params: dict[str, Any] = {"tenant_id": tenant_id, "request_id": request_id}
        if only_validated:
            clauses.append("status = 'validated'")
        where = " AND ".join(clauses)
        with self._scoped_connection(tenant_id) as conn:
            rows = (
                conn.execute(
                    text(
                        f"SELECT metadata_json FROM procurement_quotations "
                        f"WHERE {where} ORDER BY created_at"
                    ),
                    params,
                )
                .mappings()
                .fetchall()
            )
        return [Quotation.model_validate(r["metadata_json"]) for r in rows]

    # Audit -------------------------------------------------------------
    def save_audit_event(self, event: ProcurementAuditEvent) -> ProcurementAuditEvent:
        with self._scoped_transaction(event.tenant_id) as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_audit_events (
                        event_id, tenant_id, team_id, actor, action, entity_type,
                        entity_id, payload_summary, occurred_at
                    ) VALUES (
                        :event_id, :tenant_id, :team_id, :actor, :action, :entity_type,
                        :entity_id, CAST(:payload_summary AS JSONB), :occurred_at
                    )
                    """
                ),
                {
                    "event_id": event.event_id,
                    "tenant_id": event.tenant_id,
                    "team_id": event.team_id,
                    "actor": event.actor,
                    "action": event.action,
                    "entity_type": event.entity_type,
                    "entity_id": event.entity_id,
                    "payload_summary": _json_dumps(event.payload_summary),
                    "occurred_at": event.occurred_at,
                },
            )
        return event

    def list_audit_events(
        self, *, tenant_id: str, entity_id: str | None = None
    ) -> list[ProcurementAuditEvent]:
        clauses = ["tenant_id = :tenant_id"]
        params: dict[str, Any] = {"tenant_id": tenant_id}
        if entity_id is not None:
            clauses.append("entity_id = :entity_id")
            params["entity_id"] = entity_id
        where = " AND ".join(clauses)
        with self._scoped_connection(tenant_id) as conn:
            rows = (
                conn.execute(
                    text(
                        f"SELECT event_id, tenant_id, team_id, actor, action, entity_type, "
                        f"entity_id, payload_summary, occurred_at "
                        f"FROM procurement_audit_events WHERE {where} "
                        f"ORDER BY occurred_at DESC"
                    ),
                    params,
                )
                .mappings()
                .fetchall()
            )
        return [
            ProcurementAuditEvent(
                event_id=r["event_id"],
                tenant_id=r["tenant_id"],
                team_id=r["team_id"],
                actor=r["actor"],
                action=r["action"],
                entity_type=r["entity_type"],
                entity_id=r["entity_id"],
                payload_summary=r["payload_summary"] or {},
                occurred_at=r["occurred_at"],
            )
            for r in rows
        ]

    # Connection helpers ------------------------------------------------
    @contextmanager
    def _scoped_connection(self, tenant_id: str | None) -> Iterator[Connection]:
        with self._engine.connect() as connection:
            for key, value in tenant_guc_values(tenant_id=tenant_id or "*", team_id="*").items():
                connection.execute(
                    text("SELECT set_config(:key, :value, true)"),
                    {"key": key, "value": value},
                )
            yield connection

    @contextmanager
    def _scoped_transaction(self, tenant_id: str) -> Iterator[Connection]:
        with self._engine.begin() as connection:
            for key, value in tenant_guc_values(tenant_id=tenant_id, team_id="*").items():
                connection.execute(
                    text("SELECT set_config(:key, :value, true)"),
                    {"key": key, "value": value},
                )
            yield connection
