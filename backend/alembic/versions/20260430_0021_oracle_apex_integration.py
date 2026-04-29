"""Add Oracle APEX integration tables for connections, sync jobs, write-back audits,
field records, and quarantined records.

Revision ID: 20260430_0021
Revises: 20260430_0020
Create Date: 2026-04-30 00:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision = "20260430_0021"
down_revision = "20260430_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "apex_connections",
        sa.Column("connection_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
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
        "ix_apex_connections_tenant_id",
        "apex_connections",
        ["tenant_id"],
    )

    op.create_table(
        "apex_sync_jobs",
        sa.Column("job_id", sa.String(length=64), primary_key=True),
        sa.Column("connection_id", sa.String(length=64), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
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
    )
    op.create_index(
        "ix_apex_sync_jobs_tenant_created",
        "apex_sync_jobs",
        ["tenant_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "apex_writeback_audits",
        sa.Column("audit_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column(
            "payload",
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
    )
    op.create_index(
        "ix_apex_writeback_audits_tenant_created",
        "apex_writeback_audits",
        ["tenant_id", sa.text("created_at DESC")],
    )

    op.create_table(
        "apex_field_records",
        sa.Column("record_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("crop", sa.String(length=128), nullable=False),
        sa.Column("region", sa.String(length=128), nullable=False),
        sa.Column(
            "features",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "checksum",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("sync_job_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_apex_field_records_tenant_crop_region_ingested",
        "apex_field_records",
        ["tenant_id", "crop", "region", sa.text("ingested_at DESC")],
    )

    op.create_table(
        "apex_quarantined_records",
        sa.Column("quarantine_id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("sync_job_id", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_apex_quarantined_tenant_job",
        "apex_quarantined_records",
        ["tenant_id", "sync_job_id"],
    )


def downgrade() -> None:
    op.drop_table("apex_quarantined_records")
    op.drop_table("apex_field_records")
    op.drop_table("apex_writeback_audits")
    op.drop_table("apex_sync_jobs")
    op.drop_table("apex_connections")
