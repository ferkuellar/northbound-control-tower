"""saas hardening audit fields

Revision ID: 0009_saas_hardening_audit
Revises: 0008_reporting_engine
Create Date: 2026-05-13 02:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_saas_hardening_audit"
down_revision: str | None = "0008_reporting_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("audit_logs", sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("audit_logs", sa.Column("actor_role", sa.String(length=30), nullable=True))
    op.add_column("audit_logs", sa.Column("before_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("audit_logs", sa.Column("after_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("audit_logs", sa.Column("request_id", sa.String(length=128), nullable=True))
    op.create_foreign_key("fk_audit_logs_actor_user_id_users", "audit_logs", "users", ["actor_user_id"], ["id"])
    op.create_index(op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_request_id"), "audit_logs", ["request_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_request_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_actor_user_id_users", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "request_id")
    op.drop_column("audit_logs", "after_state")
    op.drop_column("audit_logs", "before_state")
    op.drop_column("audit_logs", "actor_role")
    op.drop_column("audit_logs", "actor_user_id")
