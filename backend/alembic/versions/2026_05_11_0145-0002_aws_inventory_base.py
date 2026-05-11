"""aws inventory base

Revision ID: 0002_aws_inventory_base
Revises: 0001_auth_tenant_audit_base
Create Date: 2026-05-11 01:45:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_aws_inventory_base"
down_revision: str | None = "0001_auth_tenant_audit_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cloud_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("account_id", sa.String(length=64), nullable=True),
        sa.Column("auth_type", sa.String(length=30), nullable=False),
        sa.Column("access_key_id", sa.String(length=255), nullable=True),
        sa.Column("secret_access_key", sa.String(length=1024), nullable=True),
        sa.Column("role_arn", sa.String(length=512), nullable=True),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("default_region", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cloud_accounts_provider"), "cloud_accounts", ["provider"], unique=False)
    op.create_index(op.f("ix_cloud_accounts_tenant_id"), "cloud_accounts", ["tenant_id"], unique=False)

    op.create_table(
        "inventory_scans",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resources_discovered", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventory_scans_cloud_account_id"), "inventory_scans", ["cloud_account_id"], unique=False)
    op.create_index(op.f("ix_inventory_scans_provider"), "inventory_scans", ["provider"], unique=False)
    op.create_index(op.f("ix_inventory_scans_status"), "inventory_scans", ["status"], unique=False)
    op.create_index(op.f("ix_inventory_scans_tenant_id"), "inventory_scans", ["tenant_id"], unique=False)

    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("resource_type", sa.String(length=60), nullable=False),
        sa.Column("resource_id", sa.String(length=512), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("availability_zone", sa.String(length=128), nullable=True),
        sa.Column("raw_type", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=128), nullable=True),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "cloud_account_id", "provider", "resource_id", name="uq_resource_identity"),
    )
    op.create_index(op.f("ix_resources_cloud_account_id"), "resources", ["cloud_account_id"], unique=False)
    op.create_index(op.f("ix_resources_provider"), "resources", ["provider"], unique=False)
    op.create_index(op.f("ix_resources_resource_id"), "resources", ["resource_id"], unique=False)
    op.create_index(op.f("ix_resources_resource_type"), "resources", ["resource_type"], unique=False)
    op.create_index(op.f("ix_resources_tenant_id"), "resources", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_resources_tenant_id"), table_name="resources")
    op.drop_index(op.f("ix_resources_resource_type"), table_name="resources")
    op.drop_index(op.f("ix_resources_resource_id"), table_name="resources")
    op.drop_index(op.f("ix_resources_provider"), table_name="resources")
    op.drop_index(op.f("ix_resources_cloud_account_id"), table_name="resources")
    op.drop_table("resources")
    op.drop_index(op.f("ix_inventory_scans_tenant_id"), table_name="inventory_scans")
    op.drop_index(op.f("ix_inventory_scans_status"), table_name="inventory_scans")
    op.drop_index(op.f("ix_inventory_scans_provider"), table_name="inventory_scans")
    op.drop_index(op.f("ix_inventory_scans_cloud_account_id"), table_name="inventory_scans")
    op.drop_table("inventory_scans")
    op.drop_index(op.f("ix_cloud_accounts_tenant_id"), table_name="cloud_accounts")
    op.drop_index(op.f("ix_cloud_accounts_provider"), table_name="cloud_accounts")
    op.drop_table("cloud_accounts")
