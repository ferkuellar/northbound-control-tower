"""oci cloud account fields

Revision ID: 0003_oci_cloud_account_fields
Revises: 0002_aws_inventory_base
Create Date: 2026-05-11 02:15:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_oci_cloud_account_fields"
down_revision: str | None = "0002_aws_inventory_base"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("cloud_accounts", sa.Column("tenancy_ocid", sa.String(length=255), nullable=True))
    op.add_column("cloud_accounts", sa.Column("user_ocid", sa.String(length=255), nullable=True))
    op.add_column("cloud_accounts", sa.Column("fingerprint", sa.String(length=255), nullable=True))
    op.add_column("cloud_accounts", sa.Column("private_key", sa.String(length=4096), nullable=True))
    op.add_column("cloud_accounts", sa.Column("private_key_passphrase", sa.String(length=1024), nullable=True))
    op.add_column("cloud_accounts", sa.Column("region", sa.String(length=64), nullable=True))
    op.add_column("cloud_accounts", sa.Column("compartment_ocid", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("cloud_accounts", "compartment_ocid")
    op.drop_column("cloud_accounts", "region")
    op.drop_column("cloud_accounts", "private_key_passphrase")
    op.drop_column("cloud_accounts", "private_key")
    op.drop_column("cloud_accounts", "fingerprint")
    op.drop_column("cloud_accounts", "user_ocid")
    op.drop_column("cloud_accounts", "tenancy_ocid")
