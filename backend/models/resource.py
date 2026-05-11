from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from models.cloud_account import CloudAccount


class ResourceType(StrEnum):
    COMPUTE = "compute"
    BLOCK_STORAGE = "block_storage"
    OBJECT_STORAGE = "object_storage"
    DATABASE = "database"
    IDENTITY = "identity"
    NETWORK = "network"
    MONITORING = "monitoring"


class Resource(Base, TimestampMixin):
    __tablename__ = "resources"
    __table_args__ = (
        UniqueConstraint("tenant_id", "cloud_account_id", "provider", "resource_id", name="uq_resource_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    cloud_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cloud_accounts.id"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    availability_zone: Mapped[str | None] = mapped_column(String(128), nullable=True)
    raw_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tags: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, nullable=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    cloud_account: Mapped["CloudAccount"] = relationship(back_populates="resources")
