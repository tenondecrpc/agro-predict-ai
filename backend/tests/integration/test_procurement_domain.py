"""Integration tests for spec 018 - procurement domain.

Covers:
- US1 acceptance scenarios: purchase request creation, validation,
  audit emission.
- US2 acceptance scenarios: quotation upload with supplier resolution
  and audit emission.
- US3 acceptance scenarios: data quality gate (validity_expired,
  unsupported currency, missing supplier).
- US4 acceptance scenarios: tenant isolation returns 404 (not 403)
  on cross-tenant access.

These tests use the in-memory repository so they run without a database.
The Postgres repository is exercised by the live backend smoke check.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.procurement.api import build_procurement_router
from backend.procurement.models import (
    CriteriaWeights,
    PurchaseRequestCreate,
    QuotationCreate,
    QuotationItem,
    QuotationStatus,
    SupplierCreate,
)
from backend.procurement.repository import InMemoryProcurementRepository
from backend.procurement.service import ProcurementService


@pytest.fixture
def client() -> TestClient:
    repo = InMemoryProcurementRepository()
    service = ProcurementService(repository=repo)
    app = FastAPI()
    app.include_router(build_procurement_router(service))
    return TestClient(app)


def _supplier_payload(tenant_id: str = "tenant-alpha") -> dict:
    return SupplierCreate(
        tenant_id=tenant_id,
        legal_name="Tecnomyl S.A.",
        ruc="80012345-6",
        country="PY",
        primary_categories="fertilizante,fitosanitario",
        is_importer=True,
        senave_registered=True,
        iso_certified=True,
    ).model_dump(mode="json")


def _request_payload(tenant_id: str = "tenant-alpha", team_id: str = "team-yguazu") -> dict:
    return PurchaseRequestCreate(
        tenant_id=tenant_id,
        team_id=team_id,
        requested_by="ana.rojas@yguazu.coop.py",
        title="Urea 46% para zafra soja 26/27",
        description="800 toneladas de urea granulada",
        category="fertilizante",
        target_delivery_date=date.today() + timedelta(days=30),
        target_crop="soja",
        target_zafra="2026/27",
        fenological_window="pre-siembra",
        target_hectares=Decimal("85000"),
        delivery_department="Itapua",
        criteria_weights=CriteriaWeights(price=35, delivery=30, quality=20, terms=15),
    ).model_dump(mode="json")


def _quotation_payload(
    request_id: str,
    supplier_id: str,
    *,
    tenant_id: str = "tenant-alpha",
    validity_until: date | None = None,
    currency: str = "PYG",
) -> dict:
    return QuotationCreate(
        tenant_id=tenant_id,
        request_id=request_id,
        supplier_id=supplier_id,
        created_by="ana.rojas@yguazu.coop.py",
        currency=currency,
        total_amount=Decimal("3375840000"),
        lead_time_days=10,
        validity_until=validity_until or (date.today() + timedelta(days=15)),
        warranty_months=12,
        items=[
            QuotationItem(
                description="Urea granulada 46% N",
                quantity=Decimal("16000"),
                unit_price=Decimal("210990"),
                subtotal=Decimal("3375840000"),
                presentation="bolsa 50kg",
                origin="Egipto",
            )
        ],
    ).model_dump(mode="json")


# ---------------------------------------------------------------------------
# US1 - Register a purchase request
# ---------------------------------------------------------------------------


def test_purchase_request_creation_scoped_by_tenant(client: TestClient) -> None:
    response = client.post("/api/v1/procurement/requests", json=_request_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["tenant_id"] == "tenant-alpha"
    assert body["team_id"] == "team-yguazu"
    assert body["status"] == "draft"
    assert body["request_id"]


def test_purchase_request_rejects_past_delivery_date(client: TestClient) -> None:
    payload = _request_payload()
    payload["target_delivery_date"] = (date.today() - timedelta(days=1)).isoformat()
    response = client.post("/api/v1/procurement/requests", json=payload)
    assert response.status_code == 422
    assert "target_delivery_date" in response.json()["detail"]


def test_purchase_request_rejects_invalid_weights(client: TestClient) -> None:
    payload = _request_payload()
    payload["criteria_weights"] = {"price": 50, "delivery": 50, "quality": 50, "terms": 50}
    response = client.post("/api/v1/procurement/requests", json=payload)
    assert response.status_code == 422


def test_purchase_request_creates_audit_event(client: TestClient) -> None:
    response = client.post("/api/v1/procurement/requests", json=_request_payload())
    request_id = response.json()["request_id"]
    audit = client.get(
        "/api/v1/procurement/audit",
        params={"tenant_id": "tenant-alpha", "entity_id": request_id},
    ).json()
    assert any(e["action"] == "procurement.request.created" for e in audit)


# ---------------------------------------------------------------------------
# US4 - Tenant isolation
# ---------------------------------------------------------------------------


def test_cross_tenant_request_returns_404_not_403(client: TestClient) -> None:
    created = client.post(
        "/api/v1/procurement/requests", json=_request_payload(tenant_id="tenant-alpha")
    ).json()
    response = client.get(
        f"/api/v1/procurement/requests/{created['request_id']}",
        params={"tenant_id": "tenant-beta"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "purchase_request_not_found"


def test_cross_tenant_supplier_returns_404(client: TestClient) -> None:
    created = client.post(
        "/api/v1/procurement/suppliers", json=_supplier_payload(tenant_id="tenant-alpha")
    ).json()
    response = client.get(
        f"/api/v1/procurement/suppliers/{created['supplier_id']}",
        params={"tenant_id": "tenant-beta"},
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# US3 - Data quality gate
# ---------------------------------------------------------------------------


def test_quotation_quarantined_on_expired_validity(client: TestClient) -> None:
    request = client.post("/api/v1/procurement/requests", json=_request_payload()).json()
    supplier = client.post("/api/v1/procurement/suppliers", json=_supplier_payload()).json()
    payload = _quotation_payload(
        request["request_id"],
        supplier["supplier_id"],
        validity_until=date.today() - timedelta(days=1),
    )
    response = client.post("/api/v1/procurement/quotations", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == QuotationStatus.QUARANTINED.value
    flag_codes = [f["code"] for f in body["quality_flags"]]
    assert "validity_expired" in flag_codes


def test_quotation_quarantined_on_unsupported_currency(client: TestClient) -> None:
    request = client.post("/api/v1/procurement/requests", json=_request_payload()).json()
    supplier = client.post("/api/v1/procurement/suppliers", json=_supplier_payload()).json()
    payload = _quotation_payload(
        request["request_id"], supplier["supplier_id"], currency="ZZZ"
    )
    response = client.post("/api/v1/procurement/quotations", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == QuotationStatus.QUARANTINED.value
    assert any(f["code"] == "currency_not_supported" for f in body["quality_flags"])


def test_quotation_quarantined_when_supplier_missing(client: TestClient) -> None:
    request = client.post("/api/v1/procurement/requests", json=_request_payload()).json()
    payload = _quotation_payload(request["request_id"], supplier_id="nonexistent")
    response = client.post("/api/v1/procurement/quotations", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == QuotationStatus.QUARANTINED.value
    assert any(f["code"] == "supplier_not_found" for f in body["quality_flags"])


def test_quotation_validated_when_all_checks_pass(client: TestClient) -> None:
    request = client.post("/api/v1/procurement/requests", json=_request_payload()).json()
    supplier = client.post("/api/v1/procurement/suppliers", json=_supplier_payload()).json()
    payload = _quotation_payload(request["request_id"], supplier["supplier_id"])
    response = client.post("/api/v1/procurement/quotations", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == QuotationStatus.VALIDATED.value
    assert body["quality_flags"] == []


# ---------------------------------------------------------------------------
# Listing and filtering
# ---------------------------------------------------------------------------


def test_only_validated_filter_excludes_quarantined(client: TestClient) -> None:
    request = client.post("/api/v1/procurement/requests", json=_request_payload()).json()
    supplier = client.post("/api/v1/procurement/suppliers", json=_supplier_payload()).json()
    # Validated
    client.post(
        "/api/v1/procurement/quotations",
        json=_quotation_payload(request["request_id"], supplier["supplier_id"]),
    )
    # Quarantined (expired validity)
    client.post(
        "/api/v1/procurement/quotations",
        json=_quotation_payload(
            request["request_id"],
            supplier["supplier_id"],
            validity_until=date.today() - timedelta(days=1),
        ),
    )
    all_quotes = client.get(
        f"/api/v1/procurement/requests/{request['request_id']}/quotations",
        params={"tenant_id": "tenant-alpha"},
    ).json()
    only_valid = client.get(
        f"/api/v1/procurement/requests/{request['request_id']}/quotations",
        params={"tenant_id": "tenant-alpha", "only_validated": "true"},
    ).json()
    assert len(all_quotes) == 2
    assert len(only_valid) == 1
    assert only_valid[0]["status"] == "validated"


def test_transition_to_ready_requires_two_validated_quotations(client: TestClient) -> None:
    request = client.post("/api/v1/procurement/requests", json=_request_payload()).json()
    supplier = client.post("/api/v1/procurement/suppliers", json=_supplier_payload()).json()
    # Only one validated quotation
    client.post(
        "/api/v1/procurement/quotations",
        json=_quotation_payload(request["request_id"], supplier["supplier_id"]),
    )
    response = client.post(
        f"/api/v1/procurement/requests/{request['request_id']}/transition",
        params={
            "tenant_id": "tenant-alpha",
            "new_status": "ready_for_review",
        },
    )
    assert response.status_code == 409
