import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.cloud_account import CloudAccountAuthType, CloudProvider
from models.inventory_scan import InventoryScanStatus
from models.resource import ResourceType


class AWSCloudAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    auth_type: CloudAccountAuthType
    access_key_id: str | None = Field(default=None, max_length=255)
    secret_access_key: str | None = Field(default=None, max_length=1024)
    role_arn: str | None = Field(default=None, max_length=512)
    external_id: str | None = Field(default=None, max_length=255)
    default_region: str = Field(default="us-east-1", min_length=1, max_length=64)


class OCICloudAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    auth_type: CloudAccountAuthType
    tenancy_ocid: str | None = Field(default=None, max_length=255)
    user_ocid: str | None = Field(default=None, max_length=255)
    fingerprint: str | None = Field(default=None, max_length=255)
    private_key: str | None = Field(default=None, max_length=4096)
    private_key_passphrase: str | None = Field(default=None, max_length=1024)
    region: str = Field(default="us-ashburn-1", min_length=1, max_length=64)
    compartment_ocid: str | None = Field(default=None, max_length=255)


class CloudAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider: CloudProvider
    name: str
    account_id: str | None
    auth_type: CloudAccountAuthType
    role_arn: str | None
    external_id: str | None
    default_region: str
    region: str | None
    compartment_ocid: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID
    provider: CloudProvider
    resource_category: ResourceType
    resource_type: ResourceType
    resource_id: str
    fingerprint: str | None
    name: str | None
    region: str | None
    account_id: str | None
    compartment_id: str | None
    availability_zone: str | None
    availability_domain: str | None
    raw_type: str | None
    status: str | None
    lifecycle_status: str | None
    exposure_level: str | None
    environment: str | None
    criticality: str | None
    owner: str | None
    cost_center: str | None
    application: str | None
    service_name: str | None
    tags: dict[str, Any]
    metadata_json: dict[str, Any]
    relationships: dict[str, Any] | list[dict[str, Any]]
    discovered_at: datetime
    created_at: datetime
    updated_at: datetime


class InventoryScanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID
    provider: CloudProvider
    status: InventoryScanStatus
    started_at: datetime
    completed_at: datetime | None
    resources_discovered: int
    error_message: str | None
    created_by_user_id: uuid.UUID | None
