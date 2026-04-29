"""SQLAlchemy Table definitions for AgroPredict AI prediction and model schemas."""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# ---------------------------------------------------------------------------
# model_registry
# ---------------------------------------------------------------------------
model_registry = sa.Table(
    "model_registry",
    sa.MetaData(),
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

# ---------------------------------------------------------------------------
# shadow_comparisons
# ---------------------------------------------------------------------------
shadow_comparisons = sa.Table(
    "shadow_comparisons",
    sa.MetaData(),
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
