"""ai analysis layer

Revision ID: 0007_ai_analysis_layer
Revises: 0006_risk_scoring
Create Date: 2026-05-11 04:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_ai_analysis_layer"
down_revision: str | None = "0006_risk_scoring"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=30), nullable=True),
        sa.Column("ai_provider", sa.String(length=30), nullable=False),
        sa.Column("analysis_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("input_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(length=2000), nullable=True),
        sa.Column("model_name", sa.String(length=255), nullable=True),
        sa.Column("prompt_version", sa.String(length=60), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_analyses_tenant_id"), "ai_analyses", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_ai_analyses_cloud_account_id"), "ai_analyses", ["cloud_account_id"], unique=False)
    op.create_index(op.f("ix_ai_analyses_provider"), "ai_analyses", ["provider"], unique=False)
    op.create_index(op.f("ix_ai_analyses_ai_provider"), "ai_analyses", ["ai_provider"], unique=False)
    op.create_index(op.f("ix_ai_analyses_analysis_type"), "ai_analyses", ["analysis_type"], unique=False)
    op.create_index(op.f("ix_ai_analyses_status"), "ai_analyses", ["status"], unique=False)
    op.create_index(op.f("ix_ai_analyses_created_at"), "ai_analyses", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_analyses_created_at"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_status"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_analysis_type"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_ai_provider"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_provider"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_cloud_account_id"), table_name="ai_analyses")
    op.drop_index(op.f("ix_ai_analyses_tenant_id"), table_name="ai_analyses")
    op.drop_table("ai_analyses")
