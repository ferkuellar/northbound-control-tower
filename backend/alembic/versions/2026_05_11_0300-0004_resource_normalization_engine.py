"""resource normalization engine

Revision ID: 0004_resource_norm
Revises: 0003_oci_cloud_account_fields
Create Date: 2026-05-11 03:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_resource_norm"
down_revision: str | None = "0003_oci_cloud_account_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("resources", sa.Column("fingerprint", sa.String(length=64), nullable=True))
    op.add_column("resources", sa.Column("account_id", sa.String(length=128), nullable=True))
    op.add_column("resources", sa.Column("compartment_id", sa.String(length=255), nullable=True))
    op.add_column("resources", sa.Column("availability_domain", sa.String(length=128), nullable=True))
    op.add_column("resources", sa.Column("lifecycle_status", sa.String(length=60), nullable=True))
    op.add_column("resources", sa.Column("exposure_level", sa.String(length=60), nullable=True))
    op.add_column("resources", sa.Column("environment", sa.String(length=60), nullable=True))
    op.add_column("resources", sa.Column("criticality", sa.String(length=60), nullable=True))
    op.add_column("resources", sa.Column("owner", sa.String(length=255), nullable=True))
    op.add_column("resources", sa.Column("cost_center", sa.String(length=255), nullable=True))
    op.add_column("resources", sa.Column("application", sa.String(length=255), nullable=True))
    op.add_column("resources", sa.Column("service_name", sa.String(length=255), nullable=True))
    op.add_column(
        "resources",
        sa.Column("relationships", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.alter_column("resources", "relationships", server_default=None)
    op.create_index(op.f("ix_resources_fingerprint"), "resources", ["fingerprint"], unique=False)
    op.create_index(op.f("ix_resources_lifecycle_status"), "resources", ["lifecycle_status"], unique=False)
    op.create_index(op.f("ix_resources_exposure_level"), "resources", ["exposure_level"], unique=False)
    op.create_index(op.f("ix_resources_environment"), "resources", ["environment"], unique=False)
    op.create_index(op.f("ix_resources_criticality"), "resources", ["criticality"], unique=False)
    op.create_unique_constraint("uq_resource_fingerprint", "resources", ["tenant_id", "cloud_account_id", "fingerprint"])


def downgrade() -> None:
    op.drop_constraint("uq_resource_fingerprint", "resources", type_="unique")
    op.drop_index(op.f("ix_resources_criticality"), table_name="resources")
    op.drop_index(op.f("ix_resources_environment"), table_name="resources")
    op.drop_index(op.f("ix_resources_exposure_level"), table_name="resources")
    op.drop_index(op.f("ix_resources_lifecycle_status"), table_name="resources")
    op.drop_index(op.f("ix_resources_fingerprint"), table_name="resources")
    op.drop_column("resources", "relationships")
    op.drop_column("resources", "service_name")
    op.drop_column("resources", "application")
    op.drop_column("resources", "cost_center")
    op.drop_column("resources", "owner")
    op.drop_column("resources", "criticality")
    op.drop_column("resources", "environment")
    op.drop_column("resources", "exposure_level")
    op.drop_column("resources", "lifecycle_status")
    op.drop_column("resources", "availability_domain")
    op.drop_column("resources", "compartment_id")
    op.drop_column("resources", "account_id")
    op.drop_column("resources", "fingerprint")
