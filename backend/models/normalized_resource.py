from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class CloudProvider(StrEnum):
    AWS = "aws"
    OCI = "oci"


class ResourceType(StrEnum):
    COMPUTE = "compute"
    VOLUME = "volume"
    NETWORK = "network"
    DATABASE = "database"
    STORAGE = "storage"
    UNKNOWN = "unknown"


class NormalizedResource(BaseModel):
    provider: CloudProvider
    resource_type: ResourceType
    resource_id: str
    region: str
    name: str | None = None
    account_id: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)
    risk_score: int = Field(default=0, ge=0, le=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
