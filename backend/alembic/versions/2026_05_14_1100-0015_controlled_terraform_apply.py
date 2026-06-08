"""Add controlled Terraform apply execution locks.

Revision ID: 0015_controlled_apply
Revises: 0014_approval_workflow
Create Date: 2026-05-14 11:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0015_controlled_apply"
down_revision = "0014_approval_workflow"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provisioning_execution_locks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lock_token", sa.String(length=80), nullable=False),
        sa.Column("locked_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["locked_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["provisioning_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lock_token"),
    )
    for column in ("request_id", "lock_token", "locked_by", "expires_at", "status"):
        op.create_index(op.f(f"ix_provisioning_execution_locks_{column}"), "provisioning_execution_locks", [column], unique=False)


def downgrade() -> None:
    for column in ("status", "expires_at", "locked_by", "lock_token", "request_id"):
        op.drop_index(op.f(f"ix_provisioning_execution_locks_{column}"), table_name="provisioning_execution_locks")
    op.drop_table("provisioning_execution_locks")
