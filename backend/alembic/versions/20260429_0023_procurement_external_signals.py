"""External signal cache tables: weather snapshots and FX rates.

Spec: 019-procurement-decision-pipeline (consumed by Urgency Score).
These tables are global reference caches (no tenant_id) because
weather forecasts and currency rates are public and shareable across
tenants.

Revision ID: 20260429_0023
Revises: 20260429_0022
Create Date: 2026-04-29 14:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260429_0023"
down_revision = "20260429_0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "procurement_weather_snapshots",
        sa.Column("snapshot_id", sa.String(length=64), primary_key=True),
        sa.Column("department", sa.String(length=64), nullable=False),
        sa.Column("geo_lat", sa.Numeric(10, 7), nullable=False),
        sa.Column("geo_lng", sa.Numeric(10, 7), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        # Aggregated components
        sa.Column("precipitation_sum_mm", sa.Numeric(10, 2), nullable=True),
        sa.Column("heat_stress_days", sa.Integer(), nullable=True),
        sa.Column("excess_rain_days", sa.Integer(), nullable=True),
        sa.Column("max_temp_c", sa.Numeric(5, 2), nullable=True),
        sa.Column("min_temp_c", sa.Numeric(5, 2), nullable=True),
        # Composite score
        sa.Column("weather_risk_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("risk_band", sa.String(length=24), nullable=False),
        sa.Column("interpretation", sa.String(length=500), nullable=True),
        sa.Column(
            "raw_response",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="open-meteo"),
    )
    op.create_index(
        "ix_procurement_weather_dept_fetched",
        "procurement_weather_snapshots",
        ["department", sa.text("fetched_at DESC")],
    )

    op.create_table(
        "procurement_fx_rates",
        sa.Column("rate_id", sa.String(length=64), primary_key=True),
        sa.Column("base_currency", sa.String(length=8), nullable=False),
        sa.Column("quote_currency", sa.String(length=8), nullable=False),
        sa.Column("rate_buy", sa.Numeric(14, 4), nullable=True),
        sa.Column("rate_sell", sa.Numeric(14, 4), nullable=True),
        sa.Column("rate_reference", sa.Numeric(14, 4), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "raw_response",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_procurement_fx_pair_fetched",
        "procurement_fx_rates",
        ["base_currency", "quote_currency", sa.text("fetched_at DESC")],
    )


def downgrade() -> None:
    op.drop_table("procurement_fx_rates")
    op.drop_table("procurement_weather_snapshots")
