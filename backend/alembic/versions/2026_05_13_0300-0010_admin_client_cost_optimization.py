"""admin client and cost optimization

Revision ID: 0010_admin_cost
Revises: 0009_saas_hardening_audit
Create Date: 2026-05-13 03:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010_admin_cost"
down_revision: str | None = "0009_saas_hardening_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("industry", sa.String(length=120), nullable=True))
    op.add_column("tenants", sa.Column("contact_name", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("contact_email", sa.String(length=255), nullable=True))
    op.add_column("tenants", sa.Column("notes", sa.String(length=2000), nullable=True))

    op.create_table(
        "cost_optimization_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("monthly_spend", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cost_optimization_cases_provider"), "cost_optimization_cases", ["provider"], unique=False)
    op.create_index(op.f("ix_cost_optimization_cases_tenant_id"), "cost_optimization_cases", ["tenant_id"], unique=False)

    op.create_table(
        "cost_service_breakdowns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_name", sa.String(length=80), nullable=False),
        sa.Column("monthly_cost", sa.Float(), nullable=False),
        sa.Column("percentage", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cost_optimization_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cost_service_breakdowns_case_id"), "cost_service_breakdowns", ["case_id"], unique=False)

    op.create_table(
        "cost_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("service_name", sa.String(length=80), nullable=False),
        sa.Column("estimated_savings_percent", sa.Float(), nullable=False),
        sa.Column("estimated_monthly_savings", sa.Float(), nullable=False),
        sa.Column("estimated_annual_savings", sa.Float(), nullable=False),
        sa.Column("implementation_effort", sa.String(length=60), nullable=False),
        sa.Column("risk_level", sa.String(length=60), nullable=False),
        sa.Column("assumptions", sa.String(length=2000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cost_optimization_cases.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cost_recommendations_case_id"), "cost_recommendations", ["case_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cost_recommendations_case_id"), table_name="cost_recommendations")
    op.drop_table("cost_recommendations")
    op.drop_index(op.f("ix_cost_service_breakdowns_case_id"), table_name="cost_service_breakdowns")
    op.drop_table("cost_service_breakdowns")
    op.drop_index(op.f("ix_cost_optimization_cases_tenant_id"), table_name="cost_optimization_cases")
    op.drop_index(op.f("ix_cost_optimization_cases_provider"), table_name="cost_optimization_cases")
    op.drop_table("cost_optimization_cases")
    op.drop_column("tenants", "notes")
    op.drop_column("tenants", "contact_email")
    op.drop_column("tenants", "contact_name")
    op.drop_column("tenants", "industry")
