"""Procurement domain tables for the Intelligent Purchasing Copilot.

Adds purchase requests, request items, suppliers, quotations, quotation
items, audit events, and the agro catalog reference table. Implements
spec 018-procurement-domain.

Revision ID: 20260429_0022
Revises: 20260430_0021
Create Date: 2026-04-29 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260429_0022"
down_revision = "20260430_0021"
branch_labels = None
depends_on = None


TENANT_SCOPED_TABLES = [
    "procurement_purchase_requests",
    "procurement_request_items",
    "procurement_suppliers",
    "procurement_quotations",
    "procurement_quotation_items",
    "procurement_audit_events",
]


def upgrade() -> None:
    # Suppliers (must exist before quotations FK)
    op.create_table(
        "procurement_suppliers",
        sa.Column("supplier_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("ruc", sa.String(length=32), nullable=True),
        sa.Column("legal_name", sa.String(length=300), nullable=False),
        sa.Column("commercial_name", sa.String(length=300), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=64), nullable=True),
        sa.Column("country", sa.String(length=64), nullable=False, server_default="PY"),
        sa.Column("primary_categories", sa.String(length=500), nullable=True),
        sa.Column("primary_origin_countries", sa.String(length=200), nullable=True),
        sa.Column("is_importer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("senave_registered", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("iso_certified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("risk_tier", sa.String(length=32), nullable=False, server_default="unknown"),
        sa.Column(
            "metadata_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_procurement_suppliers_tenant",
        "procurement_suppliers",
        ["tenant_id"],
    )
    op.create_index(
        "ix_procurement_suppliers_tenant_ruc",
        "procurement_suppliers",
        ["tenant_id", "ruc"],
        unique=True,
        postgresql_where=sa.text("ruc IS NOT NULL"),
    )

    # Purchase requests
    op.create_table(
        "procurement_purchase_requests",
        sa.Column("request_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("team_id", sa.String(length=128), nullable=False),
        sa.Column("requested_by", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("urgency", sa.String(length=32), nullable=False, server_default="normal"),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="PYG"),
        sa.Column("budget_cap", sa.Numeric(18, 2), nullable=True),
        sa.Column(
            "criteria_weights",
            JSONB,
            nullable=False,
            server_default=sa.text(
                "'{\"price\": 40, \"delivery\": 30, \"quality\": 20, \"terms\": 10}'::jsonb"
            ),
        ),
        sa.Column("target_delivery_date", sa.Date(), nullable=False),
        # Agro vertical
        sa.Column("target_crop", sa.String(length=64), nullable=True),
        sa.Column("target_zafra", sa.String(length=64), nullable=True),
        sa.Column("fenological_window", sa.String(length=64), nullable=True),
        sa.Column("target_hectares", sa.Numeric(12, 2), nullable=True),
        sa.Column("delivery_department", sa.String(length=64), nullable=True),
        sa.Column("delivery_location", sa.String(length=300), nullable=True),
        sa.Column("current_stock_days", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("approver_id", sa.String(length=255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("awarded_quotation_id", sa.String(length=64), nullable=True),
        sa.Column(
            "metadata_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_procurement_pr_tenant_team_status",
        "procurement_purchase_requests",
        ["tenant_id", "team_id", "status"],
    )
    op.create_index(
        "ix_procurement_pr_tenant_created",
        "procurement_purchase_requests",
        ["tenant_id", sa.text("created_at DESC")],
    )

    # Request items
    op.create_table(
        "procurement_request_items",
        sa.Column("item_id", sa.String(length=64), primary_key=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False, server_default="unit"),
        sa.Column("specifications", sa.Text(), nullable=True),
        sa.Column("target_unit_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["procurement_purchase_requests.request_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_procurement_request_items_request",
        "procurement_request_items",
        ["request_id"],
    )

    # Quotations
    op.create_table(
        "procurement_quotations",
        sa.Column("quotation_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="PYG"),
        sa.Column("exchange_rate_quoted", sa.Numeric(14, 4), nullable=True),
        sa.Column("incoterm", sa.String(length=32), nullable=True),
        sa.Column("includes_iva", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("iva_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("payment_terms", sa.String(length=200), nullable=True),
        sa.Column("total_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_pyg_normalized", sa.Numeric(18, 2), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        sa.Column("validity_until", sa.Date(), nullable=False),
        sa.Column("warranty_months", sa.Integer(), nullable=True),
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("terms_text", sa.Text(), nullable=True),
        sa.Column("attachment_ref", sa.String(length=500), nullable=True),
        sa.Column("raw_extracted_text", sa.Text(), nullable=True),
        sa.Column("extraction_confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("anomaly_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("anomaly_reason", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="uploaded"),
        sa.Column(
            "quality_flags",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "metadata_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["procurement_purchase_requests.request_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["procurement_suppliers.supplier_id"],
            ondelete="RESTRICT",
        ),
    )
    op.create_index(
        "ix_procurement_quotations_request_status",
        "procurement_quotations",
        ["request_id", "status"],
    )
    op.create_index(
        "ix_procurement_quotations_tenant_supplier",
        "procurement_quotations",
        ["tenant_id", "supplier_id"],
    )

    # Quotation items
    op.create_table(
        "procurement_quotation_items",
        sa.Column("item_id", sa.String(length=64), primary_key=True),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("request_item_id", sa.String(length=64), nullable=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 4), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 4), nullable=False),
        sa.Column("subtotal", sa.Numeric(18, 2), nullable=False),
        sa.Column("brand", sa.String(length=120), nullable=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("origin", sa.String(length=120), nullable=True),
        sa.Column("presentation", sa.String(length=120), nullable=True),
        sa.Column("lead_time_days", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(
            ["quotation_id"],
            ["procurement_quotations.quotation_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["request_item_id"],
            ["procurement_request_items.item_id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_procurement_quotation_items_quotation",
        "procurement_quotation_items",
        ["quotation_id"],
    )

    # Audit events
    op.create_table(
        "procurement_audit_events",
        sa.Column("event_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("team_id", sa.String(length=128), nullable=True),
        sa.Column("actor", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column(
            "payload_summary",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_procurement_audit_tenant_entity",
        "procurement_audit_events",
        ["tenant_id", "entity_type", "entity_id"],
    )
    op.create_index(
        "ix_procurement_audit_tenant_occurred",
        "procurement_audit_events",
        ["tenant_id", sa.text("occurred_at DESC")],
    )

    # Agro catalog (global reference, no RLS)
    op.create_table(
        "procurement_agro_catalog",
        sa.Column("sku_code", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=300), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("subcategory", sa.String(length=120), nullable=True),
        sa.Column("standard_unit", sa.String(length=32), nullable=False, server_default="unit"),
        sa.Column("typical_presentation", sa.String(length=120), nullable=True),
        sa.Column("iva_rate", sa.Numeric(5, 2), nullable=False, server_default="10.00"),
        sa.Column("market_price_min_usd", sa.Numeric(14, 4), nullable=True),
        sa.Column("market_price_max_usd", sa.Numeric(14, 4), nullable=True),
        sa.Column("market_price_currency", sa.String(length=8), nullable=False, server_default="USD"),
        sa.Column("last_market_price_update", sa.Date(), nullable=True),
        sa.Column("senave_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_procurement_agro_catalog_category",
        "procurement_agro_catalog",
        ["category", "subcategory"],
    )

    # Apply tenant-scoped RLS on every tenant-scoped table
    for table_name in TENANT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table_name}_tenant_scope
            ON {table_name}
            FOR ALL
            USING (app.current_tenant_id() = '*' OR tenant_id = app.current_tenant_id())
            WITH CHECK (app.current_tenant_id() = '*' OR tenant_id = app.current_tenant_id());
            """
        )


def downgrade() -> None:
    for table_name in TENANT_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS {table_name}_tenant_scope ON {table_name}")
        op.execute(f"ALTER TABLE IF EXISTS {table_name} DISABLE ROW LEVEL SECURITY")

    op.drop_table("procurement_agro_catalog")
    op.drop_table("procurement_audit_events")
    op.drop_table("procurement_quotation_items")
    op.drop_table("procurement_quotations")
    op.drop_table("procurement_request_items")
    op.drop_table("procurement_purchase_requests")
    op.drop_table("procurement_suppliers")
