from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.guards import require_permission
from auth.permissions import Permission
from auth.schemas import TenantRead
from core.database import get_db
from models.tenant import Tenant
from models.user import User

router = APIRouter()


@router.get("/me", response_model=TenantRead)
def read_current_tenant(current_user: User = Depends(require_permission(Permission.TENANTS_READ)), db: Session = Depends(get_db)) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.id == current_user.tenant_id))
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant
