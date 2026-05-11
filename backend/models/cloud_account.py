from __future__ import annotations

import uuid
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from models.inventory_scan import InventoryScan
    from models.resource import Resource
    from models.tenant import Tenant


class CloudProvider(StrEnum):
    AWS = "aws"
    OCI = "oci"


class CloudAccountAuthType(StrEnum):
    ACCESS_KEYS = "access_keys"
    ROLE_ARN = "role_arn"
    PROFILE = "profile"
    OCI_CONFIG = "oci_config"
    OCI_API_KEY = "oci_api_key"


class CloudAccount(Base, TimestampMixin):
    __tablename__ = "cloud_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    auth_type: Mapped[str] = mapped_column(String(30), nullable=False)
    access_key_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    secret_access_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    role_arn: Mapped[str | None] = mapped_column(String(512), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_region: Mapped[str] = mapped_column(String(64), nullable=False)
    tenancy_ocid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_ocid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    private_key: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    private_key_passphrase: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    compartment_ocid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tenant: Mapped["Tenant"] = relationship()
    resources: Mapped[list["Resource"]] = relationship(back_populates="cloud_account")
    scans: Mapped[list["InventoryScan"]] = relationship(back_populates="cloud_account")
