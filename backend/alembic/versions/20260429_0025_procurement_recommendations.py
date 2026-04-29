"""Persistence for procurement recommendations and negotiation messages.

Closes the loop on the procurement decision pipeline: every recommend
call writes to ``procurement_recommendations``, every negotiate call
writes to ``procurement_negotiation_messages``. Both are tenant-scoped
with RLS.

Revision ID: 20260429_0025
Revises: 20260429_0024
Create Date: 2026-04-29 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260429_0025"
down_revision = "20260429_0024"
branch_labels = None
depends_on = None


TENANT_SCOPED_TABLES = [
    "procurement_recommendations",
    "procurement_negotiation_messages",
]


def upgrade() -> None:
    op.create_table(
        "procurement_recommendations",
        sa.Column("recommendation_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("recommended_quotation_id", sa.String(length=64), nullable=False),
        sa.Column("recommended_supplier_id", sa.String(length=64), nullable=False),
        sa.Column("decision_band", sa.String(length=64), nullable=False),
        sa.Column("composite_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("urgency_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("offer_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("reasoning_markdown", sa.Text(), nullable=False),
        sa.Column(
            "alternatives_considered",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "risks_identified",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("source", sa.String(length=24), nullable=False, server_default="llm"),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("escalation_reason", sa.String(length=200), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_by", sa.String(length=255), nullable=True),
        sa.Column("decision_outcome", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["procurement_purchase_requests.request_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recommended_quotation_id"],
            ["procurement_quotations.quotation_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_procurement_recs_tenant_request",
        "procurement_recommendations",
        ["tenant_id", "request_id", sa.text("generated_at DESC")],
    )

    op.create_table(
        "procurement_negotiation_messages",
        sa.Column("message_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("quotation_id", sa.String(length=64), nullable=False),
        sa.Column("supplier_id", sa.String(length=64), nullable=False),
        sa.Column(
            "target_improvements",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("tone", sa.String(length=32), nullable=False, server_default="cordial"),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=24), nullable=False, server_default="llm"),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_via", sa.String(length=32), nullable=True),
        sa.Column("response_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_text", sa.Text(), nullable=True),
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
        "ix_procurement_neg_tenant_quotation",
        "procurement_negotiation_messages",
        ["tenant_id", "quotation_id", sa.text("generated_at DESC")],
    )

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

    op.drop_table("procurement_negotiation_messages")
    op.drop_table("procurement_recommendations")
