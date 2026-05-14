from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from models.audit_log import AuditLog


def list_audit_logs(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    user_id: uuid.UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    statement: Select[tuple[AuditLog]] = select(AuditLog).where(AuditLog.tenant_id == tenant_id)
    if start_date is not None:
        statement = statement.where(AuditLog.created_at >= start_date)
    if end_date is not None:
        statement = statement.where(AuditLog.created_at <= end_date)
    if user_id is not None:
        statement = statement.where(AuditLog.user_id == user_id)
    if action is not None:
        statement = statement.where(AuditLog.action == action)
    if resource_type is not None:
        statement = statement.where(AuditLog.resource_type == resource_type)
    statement = statement.order_by(AuditLog.created_at.desc()).limit(min(limit, 500))
    return list(db.scalars(statement))
