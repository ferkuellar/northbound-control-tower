"""Add Terraform validate/plan artifact metadata.

Revision ID: 0013_terraform_validate_plan
Revises: 0012_provisioning
Create Date: 2026-05-13 23:55:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0013_terraform_validate_plan"
down_revision = "0012_provisioning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("provisioning_artifacts", sa.Column("content_type", sa.String(length=120), nullable=True))
    op.add_column("provisioning_artifacts", sa.Column("size_bytes", sa.Integer(), nullable=True))
    op.add_column(
        "provisioning_artifacts",
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_provisioning_artifacts_created_by_user_id"),
        "provisioning_artifacts",
        ["created_by_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_provisioning_artifacts_created_by_user_id_users",
        "provisioning_artifacts",
        "users",
        ["created_by_user_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_provisioning_artifacts_created_by_user_id_users", "provisioning_artifacts", type_="foreignkey")
    op.drop_index(op.f("ix_provisioning_artifacts_created_by_user_id"), table_name="provisioning_artifacts")
    op.drop_column("provisioning_artifacts", "created_by_user_id")
    op.drop_column("provisioning_artifacts", "size_bytes")
    op.drop_column("provisioning_artifacts", "content_type")
