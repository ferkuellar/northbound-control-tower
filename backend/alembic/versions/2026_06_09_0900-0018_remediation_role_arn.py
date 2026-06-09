"""add remediation_role_arn to cloud_accounts

Revision ID: 0018_remediation_role_arn
Revises: 0017_encrypt_credential_columns
Create Date: 2026-06-09 09:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_remediation_role_arn"
down_revision: str | None = "0017_encrypt_credential_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "cloud_accounts",
        sa.Column("remediation_role_arn", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("cloud_accounts", "remediation_role_arn")
