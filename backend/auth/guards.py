from __future__ import annotations

from collections.abc import Callable, Iterable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.permissions import Permission, normalize_permission
from auth.roles import permissions_for_role
from core.database import get_db
from models.user import User
from services.audit_log import create_audit_log


def _request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _request_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


def require_permission(permission: Permission | str) -> Callable[[Request, User, Session], User]:
    required = normalize_permission(permission)

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if required not in permissions_for_role(current_user.role):
            create_audit_log(
                db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                action="permission_denied",
                resource_type="authorization",
                metadata={"permission": required, "role": current_user.role, "path": request.url.path},
                ip_address=_request_ip(request),
                user_agent=_request_user_agent(request),
                commit=True,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        request.state.tenant_id = current_user.tenant_id
        return current_user

    return dependency


def require_any_permission(permissions: Iterable[Permission | str]) -> Callable[[Request, User, Session], User]:
    required = {normalize_permission(permission) for permission in permissions}

    def dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        role_permissions = permissions_for_role(current_user.role)
        if not required.intersection(role_permissions):
            create_audit_log(
                db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                action="permission_denied",
                resource_type="authorization",
                metadata={"permissions": sorted(required), "role": current_user.role, "path": request.url.path},
                ip_address=_request_ip(request),
                user_agent=_request_user_agent(request),
                commit=True,
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        request.state.tenant_id = current_user.tenant_id
        return current_user

    return dependency
