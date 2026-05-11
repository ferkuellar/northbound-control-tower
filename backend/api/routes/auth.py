from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.schemas import BootstrapRequest, BootstrapResponse, CurrentUser, LoginRequest, TokenResponse
from auth.security import create_access_token, hash_password, verify_password
from core.config import settings
from core.database import get_db
from models.tenant import Tenant, TenantStatus
from models.user import User, UserRole
from services.audit_log import create_audit_log

router = APIRouter()


def _request_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _request_user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post("/bootstrap", response_model=BootstrapResponse, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: BootstrapRequest, request: Request, db: Session = Depends(get_db)) -> BootstrapResponse:
    if settings.app_env not in {"development", "local", "test"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bootstrap is disabled outside local development")

    existing_users = db.scalar(select(func.count()).select_from(User))
    if existing_users:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Bootstrap is already completed")

    if payload.user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bootstrap user must have ADMIN role")

    tenant = Tenant(
        name=payload.tenant.name,
        slug=payload.tenant.slug,
        status=TenantStatus.ACTIVE.value,
    )
    db.add(tenant)
    db.flush()

    user = User(
        tenant_id=tenant.id,
        email=payload.user.email.lower(),
        full_name=payload.user.full_name,
        hashed_password=hash_password(payload.user.password),
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    db.add(user)
    db.flush()

    create_audit_log(
        db,
        tenant_id=tenant.id,
        user_id=user.id,
        action="bootstrap_admin_created",
        resource_type="user",
        resource_id=str(user.id),
        metadata={"tenant_slug": tenant.slug, "role": user.role},
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
    )
    db.commit()
    db.refresh(tenant)
    db.refresh(user)

    return BootstrapResponse(tenant=tenant, user=user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    login_is_valid = user is not None and user.is_active and verify_password(payload.password, user.hashed_password)

    if not login_is_valid:
        create_audit_log(
            db,
            tenant_id=user.tenant_id if user else None,
            user_id=user.id if user else None,
            action="user_login_failed",
            resource_type="auth",
            metadata={"email": email},
            ip_address=_request_ip(request),
            user_agent=_request_user_agent(request),
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    access_token = create_access_token(
        subject=str(user.id),
        claims={"tenant_id": str(user.tenant_id), "role": user.role},
    )
    create_audit_log(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        action="user_login_success",
        resource_type="auth",
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        commit=True,
    )
    return TokenResponse(access_token=access_token, expires_in=settings.jwt_access_token_expire_minutes * 60)


@router.get("/me", response_model=CurrentUser)
def read_current_user(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CurrentUser:
    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="current_user_read",
        resource_type="user",
        resource_id=str(current_user.id),
        ip_address=_request_ip(request),
        user_agent=_request_user_agent(request),
        commit=True,
    )
    return CurrentUser(
        id=current_user.id,
        tenant_id=current_user.tenant_id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=UserRole(current_user.role),
    )
