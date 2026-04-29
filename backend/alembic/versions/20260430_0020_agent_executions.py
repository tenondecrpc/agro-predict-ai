"""Add agent_executions table for per-agent execution telemetry and health metrics.

Revision ID: 20260430_0020
Revises: 20260430_0019
Create Date: 2026-04-30 00:01:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260430_0020"
down_revision = "20260430_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_executions",
        sa.Column("execution_id", sa.String(length=64), primary_key=True),
        sa.Column("prediction_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_name", sa.String(length=64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "degradation_flags",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_index(
        "ix_agent_exec_tenant_agent_started",
        "agent_executions",
        ["tenant_id", "agent_name", sa.text("started_at DESC")],
    )
    op.create_index(
        "ix_agent_exec_prediction_id",
        "agent_executions",
        ["prediction_id"],
    )


def downgrade() -> None:
    op.drop_table("agent_executions")
