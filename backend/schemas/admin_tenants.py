from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminTenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    industry: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class AdminTenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: str | None = Field(default=None, min_length=1, max_length=120, pattern=r"^[a-z0-9][a-z0-9-]*$")
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")
    industry: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=255)
    contact_email: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class AdminTenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: str
    industry: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    cloud_accounts_count: int = 0
    resources_count: int = 0
    open_findings_count: int = 0
    latest_score: int | None = None
