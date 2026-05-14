"""cloud shell command audit

Revision ID: 0011_cloud_shell
Revises: 0010_admin_cost
Create Date: 2026-05-13 04:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011_cloud_shell"
down_revision: str | None = "0010_admin_cost"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cloud_shell_command_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("command_raw", sa.String(length=1000), nullable=False),
        sa.Column("command_name", sa.String(length=120), nullable=True),
        sa.Column("arguments_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("error_message", sa.String(length=1000), nullable=True),
        sa.Column("stdout", sa.Text(), nullable=True),
        sa.Column("stderr", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("related_finding_id", sa.String(length=120), nullable=True),
        sa.Column("related_request_id", sa.String(length=120), nullable=True),
        sa.Column("source_ip", sa.String(length=120), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cloud_shell_command_audits_account_id"), "cloud_shell_command_audits", ["account_id"], unique=False)
    op.create_index(op.f("ix_cloud_shell_command_audits_client_id"), "cloud_shell_command_audits", ["client_id"], unique=False)
    op.create_index(op.f("ix_cloud_shell_command_audits_command_name"), "cloud_shell_command_audits", ["command_name"], unique=False)
    op.create_index(op.f("ix_cloud_shell_command_audits_related_finding_id"), "cloud_shell_command_audits", ["related_finding_id"], unique=False)
    op.create_index(op.f("ix_cloud_shell_command_audits_related_request_id"), "cloud_shell_command_audits", ["related_request_id"], unique=False)
    op.create_index(op.f("ix_cloud_shell_command_audits_status"), "cloud_shell_command_audits", ["status"], unique=False)
    op.create_index(op.f("ix_cloud_shell_command_audits_tenant_id"), "cloud_shell_command_audits", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_cloud_shell_command_audits_user_id"), "cloud_shell_command_audits", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cloud_shell_command_audits_user_id"), table_name="cloud_shell_command_audits")
    op.drop_index(op.f("ix_cloud_shell_command_audits_tenant_id"), table_name="cloud_shell_command_audits")
    op.drop_index(op.f("ix_cloud_shell_command_audits_status"), table_name="cloud_shell_command_audits")
    op.drop_index(op.f("ix_cloud_shell_command_audits_related_request_id"), table_name="cloud_shell_command_audits")
    op.drop_index(op.f("ix_cloud_shell_command_audits_related_finding_id"), table_name="cloud_shell_command_audits")
    op.drop_index(op.f("ix_cloud_shell_command_audits_command_name"), table_name="cloud_shell_command_audits")
    op.drop_index(op.f("ix_cloud_shell_command_audits_client_id"), table_name="cloud_shell_command_audits")
    op.drop_index(op.f("ix_cloud_shell_command_audits_account_id"), table_name="cloud_shell_command_audits")
    op.drop_table("cloud_shell_command_audits")
