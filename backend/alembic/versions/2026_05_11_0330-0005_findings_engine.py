"""findings engine

Revision ID: 0005_findings_engine
Revises: 0004_resource_norm
Create Date: 2026-05-11 03:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_findings_engine"
down_revision: str | None = "0004_resource_norm"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("finding_type", sa.String(length=60), nullable=False),
        sa.Column("category", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommendation", sa.String(length=2000), nullable=False),
        sa.Column("estimated_monthly_waste", sa.Float(), nullable=True),
        sa.Column("rule_id", sa.String(length=120), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["resource_id"], ["resources.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("fingerprint", name="uq_findings_fingerprint"),
    )
    op.create_index(op.f("ix_findings_tenant_id"), "findings", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_findings_cloud_account_id"), "findings", ["cloud_account_id"], unique=False)
    op.create_index(op.f("ix_findings_resource_id"), "findings", ["resource_id"], unique=False)
    op.create_index(op.f("ix_findings_provider"), "findings", ["provider"], unique=False)
    op.create_index(op.f("ix_findings_finding_type"), "findings", ["finding_type"], unique=False)
    op.create_index(op.f("ix_findings_category"), "findings", ["category"], unique=False)
    op.create_index(op.f("ix_findings_severity"), "findings", ["severity"], unique=False)
    op.create_index(op.f("ix_findings_status"), "findings", ["status"], unique=False)
    op.create_index(op.f("ix_findings_rule_id"), "findings", ["rule_id"], unique=False)
    op.create_index(op.f("ix_findings_fingerprint"), "findings", ["fingerprint"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_findings_fingerprint"), table_name="findings")
    op.drop_index(op.f("ix_findings_rule_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_status"), table_name="findings")
    op.drop_index(op.f("ix_findings_severity"), table_name="findings")
    op.drop_index(op.f("ix_findings_category"), table_name="findings")
    op.drop_index(op.f("ix_findings_finding_type"), table_name="findings")
    op.drop_index(op.f("ix_findings_provider"), table_name="findings")
    op.drop_index(op.f("ix_findings_resource_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_cloud_account_id"), table_name="findings")
    op.drop_index(op.f("ix_findings_tenant_id"), table_name="findings")
    op.drop_table("findings")
