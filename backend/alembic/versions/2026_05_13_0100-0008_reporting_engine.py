"""reporting engine

Revision ID: 0008_reporting_engine
Revises: 0007_ai_analysis_layer
Create Date: 2026-05-13 01:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_reporting_engine"
down_revision: str | None = "0007_ai_analysis_layer"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=30), nullable=True),
        sa.Column("report_type", sa.String(length=40), nullable=False),
        sa.Column("report_format", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("generated_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("branding", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("storage_path", sa.String(length=1024), nullable=True),
        sa.Column("html_content", sa.Text(), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["generated_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_report_artifacts_tenant_id"), "report_artifacts", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_report_artifacts_cloud_account_id"), "report_artifacts", ["cloud_account_id"], unique=False)
    op.create_index(op.f("ix_report_artifacts_provider"), "report_artifacts", ["provider"], unique=False)
    op.create_index(op.f("ix_report_artifacts_report_type"), "report_artifacts", ["report_type"], unique=False)
    op.create_index(op.f("ix_report_artifacts_report_format"), "report_artifacts", ["report_format"], unique=False)
    op.create_index(op.f("ix_report_artifacts_status"), "report_artifacts", ["status"], unique=False)
    op.create_index(op.f("ix_report_artifacts_created_at"), "report_artifacts", ["created_at"], unique=False)
    op.create_index(op.f("ix_report_artifacts_generated_at"), "report_artifacts", ["generated_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_report_artifacts_generated_at"), table_name="report_artifacts")
    op.drop_index(op.f("ix_report_artifacts_created_at"), table_name="report_artifacts")
    op.drop_index(op.f("ix_report_artifacts_status"), table_name="report_artifacts")
    op.drop_index(op.f("ix_report_artifacts_report_format"), table_name="report_artifacts")
    op.drop_index(op.f("ix_report_artifacts_report_type"), table_name="report_artifacts")
    op.drop_index(op.f("ix_report_artifacts_provider"), table_name="report_artifacts")
    op.drop_index(op.f("ix_report_artifacts_cloud_account_id"), table_name="report_artifacts")
    op.drop_index(op.f("ix_report_artifacts_tenant_id"), table_name="report_artifacts")
    op.drop_table("report_artifacts")
