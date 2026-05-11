"""risk scoring engine

Revision ID: 0006_risk_scoring
Revises: 0005_findings_engine
Create Date: 2026-05-11 04:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_risk_scoring"
down_revision: str | None = "0005_findings_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cloud_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cloud_account_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider", sa.String(length=30), nullable=True),
        sa.Column("score_type", sa.String(length=60), nullable=False),
        sa.Column("score_value", sa.Integer(), nullable=False),
        sa.Column("grade", sa.String(length=30), nullable=False),
        sa.Column("trend", sa.String(length=30), nullable=False),
        sa.Column("summary", sa.String(length=1000), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["cloud_account_id"], ["cloud_accounts.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cloud_scores_tenant_id"), "cloud_scores", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_cloud_scores_cloud_account_id"), "cloud_scores", ["cloud_account_id"], unique=False)
    op.create_index(op.f("ix_cloud_scores_provider"), "cloud_scores", ["provider"], unique=False)
    op.create_index(op.f("ix_cloud_scores_score_type"), "cloud_scores", ["score_type"], unique=False)
    op.create_index(op.f("ix_cloud_scores_calculated_at"), "cloud_scores", ["calculated_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cloud_scores_calculated_at"), table_name="cloud_scores")
    op.drop_index(op.f("ix_cloud_scores_score_type"), table_name="cloud_scores")
    op.drop_index(op.f("ix_cloud_scores_provider"), table_name="cloud_scores")
    op.drop_index(op.f("ix_cloud_scores_cloud_account_id"), table_name="cloud_scores")
    op.drop_index(op.f("ix_cloud_scores_tenant_id"), table_name="cloud_scores")
    op.drop_table("cloud_scores")
