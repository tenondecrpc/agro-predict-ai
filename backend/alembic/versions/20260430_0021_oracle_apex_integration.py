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
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("credentials_ref", sa.Text(), nullable=False),
        sa.Column("sync_schedule", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("circuit_breaker_state", sa.String(length=32), nullable=False, server_default="closed"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("connection_id", sa.String(length=64), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_ingested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_validated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_quarantined", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.Column("prediction_id", sa.String(length=64), nullable=False),
        sa.Column("oracle_apex_table", sa.String(length=255), nullable=False),
        sa.Column(
            "data_written",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("approved_by", sa.String(length=255), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
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
            "raw_data",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("rejection_reason", sa.Text(), nullable=False),
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

    for table_name in [
        "apex_connections",
        "apex_sync_jobs",
        "apex_writeback_audits",
        "apex_field_records",
        "apex_quarantined_records",
    ]:
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
    for table_name in [
        "apex_quarantined_records",
        "apex_field_records",
        "apex_writeback_audits",
        "apex_sync_jobs",
        "apex_connections",
    ]:
        op.execute(f"DROP POLICY IF EXISTS {table_name}_tenant_scope ON {table_name}")
        op.execute(f"ALTER TABLE IF EXISTS {table_name} DISABLE ROW LEVEL SECURITY")

    op.drop_table("apex_quarantined_records")
    op.drop_table("apex_field_records")
    op.drop_table("apex_writeback_audits")
    op.drop_table("apex_sync_jobs")
    op.drop_table("apex_connections")
