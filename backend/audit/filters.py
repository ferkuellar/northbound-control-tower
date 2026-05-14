from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogFilters(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    user_id: uuid.UUID | None = None
    action: str | None = None
    resource_type: str | None = None
