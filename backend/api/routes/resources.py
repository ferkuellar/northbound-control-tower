import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas.inventory import ResourceRead
from auth.guards import require_permission
from auth.permissions import Permission
from core.database import get_db
from models.resource import Resource
from models.user import User

router = APIRouter()


@router.get("", response_model=list[ResourceRead])
def list_resources(
    current_user: User = Depends(require_permission(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> list[Resource]:
    return list(
        db.scalars(select(Resource).where(Resource.tenant_id == current_user.tenant_id).order_by(Resource.discovered_at.desc()))
    )


@router.get("/{resource_id}", response_model=ResourceRead)
def get_resource(
    resource_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> Resource:
    resource = db.scalar(select(Resource).where(Resource.id == resource_id, Resource.tenant_id == current_user.tenant_id))
    if resource is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource
