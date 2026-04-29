"""Add model_registry and shadow_comparisons tables for ML model lifecycle management.

Revision ID: 20260430_0019
Revises: 20260429_0018
Create Date: 2026-04-30 00:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260430_0019"
down_revision = "20260429_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_registry",
        sa.Column("model_id", sa.String(length=64), primary_key=True),
        sa.Column("crop", sa.String(length=64), nullable=False),
        sa.Column("model_type", sa.String(length=64), nullable=False, server_default=sa.text("'sklearn'")),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("artifact_path", sa.Text(), nullable=False, server_default=sa.text("''")),
        sa.Column("dataset_hash", sa.String(length=128), nullable=False, server_default=sa.text("''")),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mae", sa.Float(), nullable=True),
        sa.Column("rmse", sa.Float(), nullable=True),
        sa.Column("r2", sa.Float(), nullable=True),
        sa.Column("feature_schema", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'staged'")),
        sa.Column("promoted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("promoted_by", sa.String(length=256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_model_registry_crop_status", "model_registry", ["crop", "status"])
    op.create_index("ix_model_registry_version", "model_registry", ["version"])

    op.create_table(
        "shadow_comparisons",
        sa.Column("comparison_id", sa.String(length=64), primary_key=True),
        sa.Column("prediction_id", sa.String(length=64), nullable=False),
        sa.Column("active_version", sa.String(length=32), nullable=False),
        sa.Column("shadow_version", sa.String(length=32), nullable=False),
        sa.Column("active_output", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("shadow_output", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("delta_pct", sa.Float(), nullable=True),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_shadow_comparisons_prediction_id",
        "shadow_comparisons",
        ["prediction_id"],
    )
    op.create_index(
        "ix_shadow_comparisons_recorded_at",
        "shadow_comparisons",
        ["recorded_at", "active_version", "shadow_version"],
    )


def downgrade() -> None:
    op.drop_table("shadow_comparisons")
    op.drop_table("model_registry")
