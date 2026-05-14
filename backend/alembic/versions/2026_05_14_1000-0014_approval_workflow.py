"""Add provisioning approval workflow.

Revision ID: 0014_approval_workflow
Revises: 0013_terraform_validate_plan
Create Date: 2026-05-14 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0014_approval_workflow"
down_revision = "0013_terraform_validate_plan"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provisioning_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approval_code", sa.String(length=40), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("approval_level", sa.String(length=30), nullable=False),
        sa.Column("environment", sa.String(length=80), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("requires_double_approval", sa.Boolean(), nullable=False),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("risk_summary_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("gates_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cost_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("security_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("plan_summary_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("approved_plan_checksum_sha256", sa.String(length=128), nullable=True),
        sa.Column("approved_plan_json_checksum_sha256", sa.String(length=128), nullable=True),
        sa.Column("approved_risk_summary_checksum_sha256", sa.String(length=128), nullable=True),
        sa.Column("approved_gates_result_checksum_sha256", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["approved_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["provisioning_requests.id"]),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approval_code", name="uq_provisioning_approval_code"),
    )
    for column in (
        "approval_code",
        "request_id",
        "tenant_id",
        "client_id",
        "cloud_account_id",
        "requested_by",
        "approved_by",
        "decision",
        "status",
    ):
        op.create_index(op.f(f"ix_provisioning_approvals_{column}"), "provisioning_approvals", [column], unique=False)


def downgrade() -> None:
    for column in (
        "status",
        "decision",
        "approved_by",
        "requested_by",
        "cloud_account_id",
        "client_id",
        "tenant_id",
        "request_id",
        "approval_code",
    ):
        op.drop_index(op.f(f"ix_provisioning_approvals_{column}"), table_name="provisioning_approvals")
    op.drop_table("provisioning_approvals")
