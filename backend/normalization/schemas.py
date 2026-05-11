from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from normalization.enums import Criticality, Environment, ExposureLevel, Provider, ResourceCategory, ResourceLifecycleStatus


class NormalizedResource(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    provider: Provider
    resource_category: ResourceCategory
    resource_id: str = Field(min_length=1, max_length=512)
    raw_type: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=512)
    region: str = Field(min_length=1, max_length=64)
    account_id: str | None = Field(default=None, max_length=128)
    compartment_id: str | None = Field(default=None, max_length=255)
    tenant_id: uuid.UUID | None = None
    cloud_account_id: uuid.UUID | None = None
    availability_zone: str | None = Field(default=None, max_length=128)
    availability_domain: str | None = Field(default=None, max_length=128)
    lifecycle_status: ResourceLifecycleStatus = ResourceLifecycleStatus.UNKNOWN
    exposure_level: ExposureLevel = ExposureLevel.UNKNOWN
    environment: Environment = Environment.UNKNOWN
    criticality: Criticality = Criticality.UNKNOWN
    owner: str | None = Field(default=None, max_length=255)
    cost_center: str | None = Field(default=None, max_length=255)
    application: str | None = Field(default=None, max_length=255)
    service_name: str | None = Field(default=None, max_length=255)
    tags: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    relationships: dict[str, Any] | list[dict[str, Any]] = Field(default_factory=dict)
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fingerprint: str | None = None

    @field_validator("tags", "metadata", mode="before")
    @classmethod
    def ensure_json_object(cls, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @field_validator("relationships", mode="before")
    @classmethod
    def ensure_relationships_json(cls, value: Any) -> dict[str, Any] | list[dict[str, Any]]:
        if isinstance(value, dict):
            return value
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        return {}

    @model_validator(mode="before")
    @classmethod
    def fallback_name(cls, data: Any) -> Any:
        if isinstance(data, dict) and not data.get("name"):
            data["name"] = data.get("resource_id")
        return data
