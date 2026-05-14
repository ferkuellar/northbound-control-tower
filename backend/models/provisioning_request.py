from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from models.finding import Finding
    from models.user import User


class ProvisioningRequest(Base, TimestampMixin):
    __tablename__ = "provisioning_requests"
    __table_args__ = (UniqueConstraint("request_number", name="uq_provisioning_request_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_number: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    cloud_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cloud_accounts.id"), nullable=True, index=True)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("findings.id"), nullable=True, index=True)
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    template_key: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    template_version: Mapped[str] = mapped_column(String(40), nullable=False, default="v0")
    status: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    input_variables: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    tfvars_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    workspace_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    finding: Mapped["Finding | None"] = relationship()
    requested_by: Mapped["User | None"] = relationship()


class ProvisioningArtifact(Base, TimestampMixin):
    __tablename__ = "provisioning_artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    provisioning_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("provisioning_requests.id"), nullable=False, index=True
    )
    artifact_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    request: Mapped["ProvisioningRequest"] = relationship()


class ProvisioningApproval(Base, TimestampMixin):
    __tablename__ = "provisioning_approvals"
    __table_args__ = (UniqueConstraint("approval_code", name="uq_provisioning_approval_code"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_code: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("provisioning_requests.id"), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True)
    client_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    cloud_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("cloud_accounts.id"), nullable=True, index=True)
    requested_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING", index=True)
    approval_level: Mapped[str] = mapped_column(String(30), nullable=False, default="STANDARD")
    environment: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    requires_double_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_summary_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    gates_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    cost_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    security_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    plan_summary_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    approved_plan_checksum_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_plan_json_checksum_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_risk_summary_checksum_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_gates_result_checksum_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    request: Mapped["ProvisioningRequest"] = relationship()


class ProvisioningExecutionLock(Base, TimestampMixin):
    __tablename__ = "provisioning_execution_locks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("provisioning_requests.id"), nullable=False, index=True)
    lock_token: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    locked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    locked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    request: Mapped["ProvisioningRequest"] = relationship()
