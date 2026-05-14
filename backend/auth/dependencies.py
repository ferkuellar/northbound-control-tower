import uuid
from collections.abc import Callable, Sequence

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.security import decode_access_token
from core.database import get_db
from models.user import User, UserRole
from models.tenant import Tenant

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        user_id = uuid.UUID(str(subject))
        token_tenant_id = uuid.UUID(str(payload.get("tenant_id"))) if payload.get("tenant_id") else None
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.scalar(select(User).where(User.id == user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if token_tenant_id and token_tenant_id != user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    request.state.tenant_id = user.tenant_id
    return user


def require_roles(roles: Sequence[UserRole | str]) -> Callable[[User], User]:
    allowed_roles = {role.value if isinstance(role, UserRole) else role for role in roles}

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user

    return dependency


def get_current_tenant(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Tenant:
    tenant = db.get(Tenant, current_user.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant not found")
    return tenant
