"""post remediation validation

Revision ID: 0016_post_validation
Revises: 0015_controlled_apply
Create Date: 2026-05-14 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0016_post_validation"
down_revision: str | None = "0015_controlled_apply"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "collector_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collector_run_code", sa.String(length=40), nullable=False),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("triggered_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_source", sa.String(length=80), nullable=False),
        sa.Column("resources_collected_count", sa.Integer(), nullable=False),
        sa.Column("findings_generated_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collector_run_code", name="uq_collector_run_code"),
    )
    op.create_index(op.f("ix_collector_runs_cloud_account_id"), "collector_runs", ["cloud_account_id"], unique=False)
    op.create_index(op.f("ix_collector_runs_collector_run_code"), "collector_runs", ["collector_run_code"], unique=False)
    op.create_index(op.f("ix_collector_runs_provider"), "collector_runs", ["provider"], unique=False)
    op.create_index(op.f("ix_collector_runs_status"), "collector_runs", ["status"], unique=False)
    op.create_index(op.f("ix_collector_runs_tenant_id"), "collector_runs", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_collector_runs_trigger_source"), "collector_runs", ["trigger_source"], unique=False)
    op.create_index(op.f("ix_collector_runs_triggered_by"), "collector_runs", ["triggered_by"], unique=False)

    op.create_table(
        "post_remediation_validations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("validation_code", sa.String(length=40), nullable=False),
        sa.Column("request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("region", sa.String(length=80), nullable=True),
        sa.Column("environment", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("result", sa.String(length=40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("validated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("collector_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("before_finding_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("after_finding_snapshot_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("inventory_snapshot_before_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("inventory_snapshot_after_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("findings_diff_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("validation_checks_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["collector_run_id"], ["collector_runs.id"]),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
        sa.ForeignKeyConstraint(["request_id"], ["provisioning_requests.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["validated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("validation_code", name="uq_post_remediation_validation_code"),
    )
    op.create_index(op.f("ix_post_remediation_validations_cloud_account_id"), "post_remediation_validations", ["cloud_account_id"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_client_id"), "post_remediation_validations", ["client_id"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_collector_run_id"), "post_remediation_validations", ["collector_run_id"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_finding_id"), "post_remediation_validations", ["finding_id"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_provider"), "post_remediation_validations", ["provider"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_request_id"), "post_remediation_validations", ["request_id"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_result"), "post_remediation_validations", ["result"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_status"), "post_remediation_validations", ["status"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_tenant_id"), "post_remediation_validations", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_validated_by"), "post_remediation_validations", ["validated_by"], unique=False)
    op.create_index(op.f("ix_post_remediation_validations_validation_code"), "post_remediation_validations", ["validation_code"], unique=False)


def downgrade() -> None:
    op.drop_table("post_remediation_validations")
    op.drop_table("collector_runs")
