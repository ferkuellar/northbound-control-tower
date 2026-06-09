"""widen credential columns for Fernet ciphertext

Revision ID: 0017_encrypt_credential_columns
Revises: 0016_post_validation
Create Date: 2026-06-08 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017_encrypt_credential_columns"
down_revision: str | None = "0016_post_validation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "cloud_accounts",
        "secret_access_key",
        existing_type=sa.String(length=1024),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "cloud_accounts",
        "private_key",
        existing_type=sa.String(length=4096),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "cloud_accounts",
        "private_key_passphrase",
        existing_type=sa.String(length=1024),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "cloud_accounts",
        "private_key_passphrase",
        existing_type=sa.Text(),
        type_=sa.String(length=1024),
        existing_nullable=True,
    )
    op.alter_column(
        "cloud_accounts",
        "private_key",
        existing_type=sa.Text(),
        type_=sa.String(length=4096),
        existing_nullable=True,
    )
    op.alter_column(
        "cloud_accounts",
        "secret_access_key",
        existing_type=sa.Text(),
        type_=sa.String(length=1024),
        existing_nullable=True,
    )
