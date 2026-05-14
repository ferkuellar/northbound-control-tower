from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth.guards import require_permission
from auth.permissions import Permission
from core.database import get_db
from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant
from models.user import User
from schemas.admin_tenants import AdminTenantCreate, AdminTenantRead, AdminTenantUpdate
from services.audit_log import create_audit_log

router = APIRouter()


def _tenant_summary(db: Session, tenant: Tenant) -> AdminTenantRead:
    cloud_accounts_count = db.scalar(select(func.count()).select_from(CloudAccount).where(CloudAccount.tenant_id == tenant.id)) or 0
    resources_count = db.scalar(select(func.count()).select_from(Resource).where(Resource.tenant_id == tenant.id)) or 0
    open_findings_count = (
        db.scalar(
            select(func.count())
            .select_from(Finding)
            .where(Finding.tenant_id == tenant.id, Finding.status.in_(["open", "acknowledged"]))
        )
        or 0
    )
    latest_score = db.scalar(
        select(CloudScore.score_value)
        .where(CloudScore.tenant_id == tenant.id, CloudScore.score_type == "overall")
        .order_by(CloudScore.calculated_at.desc())
        .limit(1)
    )
    payload = AdminTenantRead.model_validate(tenant)
    return payload.model_copy(
        update={
            "cloud_accounts_count": cloud_accounts_count,
            "resources_count": resources_count,
            "open_findings_count": open_findings_count,
            "latest_score": latest_score,
        }
    )


@router.get("", response_model=list[AdminTenantRead])
def list_admin_tenants(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TENANTS_READ)),
) -> list[AdminTenantRead]:
    tenants = db.scalars(select(Tenant).order_by(Tenant.created_at.desc())).all()
    return [_tenant_summary(db, tenant) for tenant in tenants]


@router.post("", response_model=AdminTenantRead, status_code=status.HTTP_201_CREATED)
def create_admin_tenant(
    payload: AdminTenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TENANTS_WRITE)),
) -> AdminTenantRead:
    existing = db.scalar(select(Tenant).where(Tenant.slug == payload.slug))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists")
    tenant = Tenant(**payload.model_dump())
    db.add(tenant)
    db.flush()
    create_audit_log(
        db,
        tenant_id=tenant.id,
        user_id=current_user.id,
        actor_role=current_user.role,
        action="tenant_created",
        resource_type="tenant",
        resource_id=str(tenant.id),
        after_state={"name": tenant.name, "slug": tenant.slug, "industry": tenant.industry},
    )
    db.commit()
    db.refresh(tenant)
    return _tenant_summary(db, tenant)


@router.get("/{tenant_id}", response_model=AdminTenantRead)
def get_admin_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TENANTS_READ)),
) -> AdminTenantRead:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return _tenant_summary(db, tenant)


@router.patch("/{tenant_id}", response_model=AdminTenantRead)
def update_admin_tenant(
    tenant_id: uuid.UUID,
    payload: AdminTenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(Permission.TENANTS_WRITE)),
) -> AdminTenantRead:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    changes = payload.model_dump(exclude_unset=True)
    if "slug" in changes:
        existing = db.scalar(select(Tenant).where(Tenant.slug == changes["slug"], Tenant.id != tenant_id))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant slug already exists")
    before = {"name": tenant.name, "slug": tenant.slug, "status": tenant.status}
    for key, value in changes.items():
        setattr(tenant, key, value)
    create_audit_log(
        db,
        tenant_id=tenant.id,
        user_id=current_user.id,
        actor_role=current_user.role,
        action="tenant_updated",
        resource_type="tenant",
        resource_id=str(tenant.id),
        before_state=before,
        after_state=changes,
    )
    db.commit()
    db.refresh(tenant)
    return _tenant_summary(db, tenant)
