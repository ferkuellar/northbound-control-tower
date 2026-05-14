from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from audit.schemas import AuditLogListResponse, AuditLogRead
from audit.service import list_audit_logs
from auth.guards import require_permission
from auth.permissions import Permission
from core.database import get_db
from models.user import User

router = APIRouter()


@router.get("/logs", response_model=AuditLogListResponse)
def read_audit_logs(
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    action: str | None = Query(default=None, max_length=120),
    resource_type: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    logs = list_audit_logs(
        db,
        tenant_id=current_user.tenant_id,
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        limit=limit,
    )
    return AuditLogListResponse(items=[AuditLogRead.model_validate(log) for log in logs], total=len(logs))
