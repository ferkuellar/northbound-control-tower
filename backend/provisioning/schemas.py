from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ProvisioningArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provisioning_request_id: uuid.UUID
    artifact_type: str
    name: str
    content_json: dict[str, Any]
    checksum: str | None
    generated_at: datetime


class ProvisioningRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    request_number: str
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID | None
    finding_id: uuid.UUID | None
    requested_by_user_id: uuid.UUID | None
    provider: str
    template_key: str
    template_version: str
    status: str
    risk_level: str
    title: str
    description: str
    input_variables: dict[str, Any]
    tfvars_json: dict[str, Any]
    workspace_path: str | None
    evidence: dict[str, Any]
    approval_required: bool
    created_at: datetime
    updated_at: datetime


class ProvisioningRequestListResponse(BaseModel):
    items: list[ProvisioningRequestRead]
    total: int


class ProvisioningArtifactListResponse(BaseModel):
    items: list[ProvisioningArtifactRead]
    total: int


class ProvisioningRequestCreateFromFinding(BaseModel):
    finding_id: uuid.UUID


class ProvisioningTemplateRead(BaseModel):
    key: str
    provider: str
    finding_types: list[str]
    title: str
    description: str
    risk_level: str
    required_variables: list[str]
    module_path: str
