"""Add tenant-scoped prediction result storage.

Revision ID: 20260429_0018
Revises: 20260427_0017
Create Date: 2026-04-29 01:35:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260429_0018"
down_revision = "20260427_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "predictions",
        sa.Column("prediction_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("team_id", sa.String(length=128), nullable=False, server_default=sa.text("'unknown'")),
        sa.Column("payload", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
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
        "ix_predictions_tenant_team_created",
        "predictions",
        ["tenant_id", "team_id", "created_at"],
    )
    op.create_index(
        "ix_predictions_tenant_created",
        "predictions",
        ["tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_predictions_tenant_created", table_name="predictions")
    op.drop_index("ix_predictions_tenant_team_created", table_name="predictions")
    op.drop_table("predictions")
