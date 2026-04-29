"""Procurement dual scoring and ML supplier predictor tables.

Adds:
- procurement_supplier_performance_history: historical deliveries for
  ML training and feature extraction.
- procurement_supplier_predictions: cached predictor outputs per
  supplier with model version and freshness.
- procurement_scores: dual score (Urgency + Offer) per (request,
  quotation) with all components and the decision band.

Revision ID: 20260429_0024
Revises: 20260429_0023
Create Date: 2026-04-29 16:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260429_0024"
down_revision = "20260429_0023"
branch_labels = None
depends_on = None


TENANT_SCOPED_TABLES = ["procurement_scores"]


def upgrade() -> None:
    op.create_table(
        "procurement_supplier_performance_history",
        sa.Column("history_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("awarded_date", sa.Date(), nullable=False),
        sa.Column("promised_delivery_date", sa.Date(), nullable=False),
        sa.Column("actual_delivery_date", sa.Date(), nullable=True),
        sa.Column("delivered_on_time", sa.Boolean(), nullable=True),
        sa.Column("days_delay", sa.Integer(), nullable=True),
        sa.Column("price_at_award", sa.Numeric(18, 2), nullable=True),
        sa.Column("price_actual", sa.Numeric(18, 2), nullable=True),
        sa.Column("quality_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_procurement_history_supplier_awarded",
        "procurement_supplier_performance_history",
        ["supplier_id", sa.text("awarded_date DESC")],
    )
    op.create_index(
        "ix_procurement_history_tenant_supplier",
        "procurement_supplier_performance_history",
        ["tenant_id", "supplier_id"],
    )

    op.create_table(
        "procurement_supplier_predictions",
        sa.Column("supplier_id", sa.String(length=64), primary_key=True),
        sa.Column("p_on_time", sa.Numeric(5, 4), nullable=False),
        sa.Column("expected_delay_days_if_late", sa.Numeric(6, 2), nullable=True),
        sa.Column("p_price_holds", sa.Numeric(5, 4), nullable=True),
        sa.Column("confidence_band", sa.String(length=24), nullable=False),
        sa.Column("based_on_n_observations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "top_features",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "procurement_scores",
        sa.Column("score_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        # Urgency components
        sa.Column("weather_risk", sa.Numeric(5, 2), nullable=True),
        sa.Column("delivery_urgency", sa.Numeric(5, 2), nullable=True),
        sa.Column("market_volatility", sa.Numeric(5, 2), nullable=True),
        sa.Column("urgency_score", sa.Numeric(5, 2), nullable=False),
        # Offer components
        sa.Column("supplier_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("commercial_terms_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("delivery_risk", sa.Numeric(5, 2), nullable=True),
        sa.Column("offer_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("decision_band", sa.String(length=64), nullable=False),
        sa.Column(
            "components_json",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "computed_at",
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
            ["quotation_id"],
            ["procurement_quotations.quotation_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_procurement_scores_request",
        "procurement_scores",
        ["request_id", sa.text("computed_at DESC")],
    )
    op.create_index(
        "ix_procurement_scores_tenant_request_quotation",
        "procurement_scores",
        ["tenant_id", "request_id", "quotation_id"],
    )

    # Tenant-scoped RLS for procurement_scores. The other two tables are
    # supporting reference data: history is keyed by supplier (tenant_id
    # is informational only), predictions are global per supplier.
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

    op.drop_table("procurement_scores")
    op.drop_table("procurement_supplier_predictions")
    op.drop_table("procurement_supplier_performance_history")
