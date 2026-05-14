import uuid
from typing import Any

from sqlalchemy.orm import Session

from models.audit_log import AuditLog
from observability.logging import get_request_id


def create_audit_log(
    db: Session,
    *,
    action: str,
    resource_type: str,
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    actor_role: str | None = None,
    request_id: str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
) -> AuditLog:
    audit_log = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        actor_user_id=user_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata_json=metadata or {},
        before_state=before_state,
        after_state=after_state,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id or get_request_id(),
    )
    db.add(audit_log)
    if commit:
        db.commit()
        db.refresh(audit_log)
    return audit_log
