from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    user_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    actor_role: str | None
    action: str
    resource_type: str
    resource_id: str | None
    metadata_json: dict[str, Any]
    before_state: dict[str, Any] | None
    after_state: dict[str, Any] | None
    ip_address: str | None
    user_agent: str | None
    request_id: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogRead]
    total: int
