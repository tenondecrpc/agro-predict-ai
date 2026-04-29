"""Seed the AgroBuy demo dataset into Postgres.

Loads:
- 8 agro suppliers (recognizable Paraguayan industry names with synthetic RUCs).
- 6 agro catalog entries with market price bands.
- 5 purchase requests for Cooperativa Yguazu (Itapua, Paraguay).
- 15 quotations across the 5 requests (with one deliberate price anomaly).
- ~150 supplier_performance_history records calibrated by quartile.

Run:

    uv run --project backend python -m backend.procurement.fixtures.seed

By default the seed targets ``tenant=tenant-yguazu``, ``team=team-compras``.
Use ``--reset`` to wipe the tenant first (suppliers, requests, quotations,
recommendations, scores, history). The agro_catalog is global and is upserted
in place.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine, text

from backend.procurement.decision_repository import PostgresDecisionRepository
from backend.procurement.fixtures.agro_data import (
    AGRO_CATALOG,
    QUOTATIONS,
    REQUESTS,
    SUPPLIERS,
    historical_calibration,
)
from backend.procurement.ml.models import SupplierPerformanceRecord
from backend.procurement.models import (
    CriteriaWeights,
    PurchaseRequestCreate,
    QuotationCreate,
    QuotationItem,
    RequestItem,
    SupplierCreate,
    Urgency,
)
from backend.procurement.repository import PostgresProcurementRepository
from backend.procurement.service import ProcurementService

logger = logging.getLogger(__name__)

DEFAULT_TENANT = "tenant-yguazu"
DEFAULT_TEAM = "team-compras"
DEFAULT_ACTOR = "ana.rojas@yguazu.coop.py"


def _normalize_db_url(raw: str) -> str:
    if "+" not in raw and raw.startswith("postgresql"):
        return raw.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw


def _wipe_tenant(engine: Any, tenant_id: str) -> None:
    """Delete all procurement rows for the tenant. Idempotent."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "DELETE FROM procurement_supplier_performance_history "
                "WHERE tenant_id = :tid"
            ),
            {"tid": tenant_id},
        )
        # Cascading FKs handle the rest from purchase_requests + suppliers
        conn.execute(
            text("DELETE FROM procurement_purchase_requests WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        )
        conn.execute(
            text("DELETE FROM procurement_suppliers WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        )
        conn.execute(
            text("DELETE FROM procurement_audit_events WHERE tenant_id = :tid"),
            {"tid": tenant_id},
        )


def _upsert_catalog(engine: Any) -> int:
    with engine.begin() as conn:
        for entry in AGRO_CATALOG:
            conn.execute(
                text(
                    """
                    INSERT INTO procurement_agro_catalog (
                        sku_code, name, category, subcategory, standard_unit,
                        typical_presentation, iva_rate, market_price_min_usd,
                        market_price_max_usd, market_price_currency,
                        last_market_price_update, senave_required, notes
                    ) VALUES (
                        :sku_code, :name, :category, :subcategory, :standard_unit,
                        :typical_presentation, :iva_rate, :market_price_min_usd,
                        :market_price_max_usd, :market_price_currency,
                        :last_market_price_update, :senave_required, :notes
                    )
                    ON CONFLICT (sku_code) DO UPDATE
                    SET name = EXCLUDED.name,
                        market_price_min_usd = EXCLUDED.market_price_min_usd,
                        market_price_max_usd = EXCLUDED.market_price_max_usd,
                        last_market_price_update = EXCLUDED.last_market_price_update,
                        notes = EXCLUDED.notes
                    """
                ),
                {
                    "sku_code": entry.sku_code,
                    "name": entry.name,
                    "category": entry.category,
                    "subcategory": entry.subcategory,
                    "standard_unit": entry.standard_unit,
                    "typical_presentation": entry.typical_presentation,
                    "iva_rate": entry.iva_rate,
                    "market_price_min_usd": entry.market_price_min_usd,
                    "market_price_max_usd": entry.market_price_max_usd,
                    "market_price_currency": "USD",
                    "last_market_price_update": date.today(),
                    "senave_required": entry.senave_required,
                    "notes": entry.notes,
                },
            )
    return len(AGRO_CATALOG)


def seed(
    database_url: str,
    *,
    tenant_id: str = DEFAULT_TENANT,
    team_id: str = DEFAULT_TEAM,
    actor: str = DEFAULT_ACTOR,
    reset: bool = True,
) -> dict[str, int]:
    engine = create_engine(_normalize_db_url(database_url), future=True)

    if reset:
        logger.info("wiping tenant %s", tenant_id)
        _wipe_tenant(engine, tenant_id)

    catalog_count = _upsert_catalog(engine)
    logger.info("upserted %d catalog entries", catalog_count)

    proc_repo = PostgresProcurementRepository(_normalize_db_url(database_url))
    decision_repo = PostgresDecisionRepository(_normalize_db_url(database_url))
    svc = ProcurementService(repository=proc_repo)

    suppliers_by_name: dict[str, str] = {}
    for s in SUPPLIERS:
        created = svc.create_supplier(
            SupplierCreate(
                tenant_id=tenant_id,
                legal_name=s.legal_name,
                ruc=s.ruc,
                commercial_name=s.commercial_name,
                contact_email=s.contact_email,
                contact_phone=s.contact_phone,
                country="PY",
                primary_categories=s.primary_categories,
                primary_origin_countries=s.primary_origin_countries,
                is_importer=s.is_importer,
                senave_registered=s.senave_registered,
                iso_certified=s.iso_certified,
            ),
            actor=actor,
        )
        suppliers_by_name[s.legal_name] = created.supplier_id
    logger.info("created %d suppliers", len(suppliers_by_name))

    request_ids: list[str] = []
    for r in REQUESTS:
        target_delivery = date.today() + timedelta(days=r.target_delivery_offset_days)
        created = svc.create_request(
            PurchaseRequestCreate(
                tenant_id=tenant_id,
                team_id=team_id,
                requested_by=actor,
                title=r.title,
                description=r.description,
                category=r.category,
                urgency=Urgency(r.urgency),
                currency="PYG",
                target_delivery_date=target_delivery,
                target_crop=r.target_crop,
                target_zafra=r.target_zafra,
                fenological_window=r.fenological_window,
                target_hectares=r.target_hectares,
                delivery_department=r.delivery_department,
                delivery_location=r.delivery_location,
                current_stock_days=r.current_stock_days,
                criteria_weights=CriteriaWeights(),
                items=[
                    RequestItem(
                        description=r.item_description,
                        quantity=r.item_quantity,
                        unit=r.item_unit,
                    )
                ],
            ),
            actor=actor,
        )
        request_ids.append(created.request_id)
    logger.info("created %d purchase requests", len(request_ids))

    quote_ids: list[tuple[str, str, str]] = []  # (quotation_id, request_id, supplier_id)
    for q in QUOTATIONS:
        request_id = request_ids[q.request_index]
        supplier_id = suppliers_by_name[q.supplier_legal_name]
        validity = date.today() + timedelta(days=q.validity_offset_days)
        # Compute item subtotal from unit_price x quantity in native currency.
        request_seed = REQUESTS[q.request_index]
        item_quantity = request_seed.item_quantity
        subtotal_native = (q.item_unit_price * item_quantity).quantize(Decimal("0.01"))
        created = svc.upload_quotation(
            QuotationCreate(
                tenant_id=tenant_id,
                request_id=request_id,
                supplier_id=supplier_id,
                created_by=actor,
                currency=q.currency,
                exchange_rate_quoted=q.exchange_rate_quoted,
                incoterm=q.incoterm,
                includes_iva=q.includes_iva,
                payment_terms=q.payment_terms,
                total_amount=q.total_amount_native,
                total_pyg_normalized=q.total_amount_pyg_normalized,
                lead_time_days=q.lead_time_days,
                validity_until=validity,
                warranty_months=q.warranty_months,
                discount_pct=q.discount_pct,
                items=[
                    QuotationItem(
                        description=request_seed.item_description,
                        quantity=item_quantity,
                        unit_price=q.item_unit_price,
                        subtotal=subtotal_native,
                        presentation=q.presentation,
                        origin=q.origin,
                        notes=q.note,
                    )
                ],
            ),
            actor=actor,
        )
        quote_ids.append((created.quotation_id, request_id, supplier_id))
    logger.info("uploaded %d quotations", len(quote_ids))

    history = _build_history(suppliers_by_name, tenant_id=tenant_id)
    decision_repo.save_history_records(history)
    logger.info("inserted %d history records", len(history))

    return {
        "catalog_entries": catalog_count,
        "suppliers": len(suppliers_by_name),
        "requests": len(request_ids),
        "quotations": len(quote_ids),
        "history_records": len(history),
    }


def _build_history(
    suppliers_by_name: dict[str, str],
    *,
    tenant_id: str,
    seed: int = 17,
) -> list[SupplierPerformanceRecord]:
    rng = random.Random(seed)
    records: list[SupplierPerformanceRecord] = []
    categories = ["fertilizante", "fitosanitario", "semilla", "maquinaria"]
    for supplier in SUPPLIERS:
        supplier_id = suppliers_by_name[supplier.legal_name]
        on_time_rate, mean_delay, n = historical_calibration(supplier.profile)
        primary_cat = supplier.primary_categories.split(",")[0] if supplier.primary_categories else "fertilizante"
        for j in range(n):
            awarded_offset = 30 + j * 20 + rng.randint(0, 10)
            lead_time = rng.randint(7, 25)
            on_time = rng.random() < on_time_rate
            delay = 0 if on_time else max(1, int(rng.gauss(mean_delay, 1.5)))
            awarded = date.today() - timedelta(days=awarded_offset)
            promised = awarded + timedelta(days=lead_time)
            actual = promised + timedelta(days=delay)
            cat = primary_cat if rng.random() < 0.85 else rng.choice(categories)
            records.append(
                SupplierPerformanceRecord(
                    tenant_id=tenant_id,
                    supplier_id=supplier_id,
                    category=cat,
                    awarded_date=awarded,
                    promised_delivery_date=promised,
                    actual_delivery_date=actual,
                    delivered_on_time=on_time,
                    days_delay=delay,
                    price_at_award=Decimal(rng.randint(1000, 100000) * 1000),
                )
            )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed AgroBuy demo dataset")
    parser.add_argument("--tenant", default=DEFAULT_TENANT)
    parser.add_argument("--team", default=DEFAULT_TEAM)
    parser.add_argument("--actor", default=DEFAULT_ACTOR)
    parser.add_argument(
        "--no-reset",
        dest="reset",
        action="store_false",
        help="do not wipe the tenant before seeding",
    )
    parser.set_defaults(reset=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    database_url = os.environ.get("BACKEND_DATABASE_URL")
    if not database_url:
        raise SystemExit("BACKEND_DATABASE_URL must be set")

    metrics = seed(
        database_url,
        tenant_id=args.tenant,
        team_id=args.team,
        actor=args.actor,
        reset=args.reset,
    )
    print("AgroBuy seed complete:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":  # pragma: no cover
    main()
