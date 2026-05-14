import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.schemas.inventory import InventoryScanRead
from auth.guards import require_permission
from auth.permissions import Permission
from core.database import get_db
from models.cloud_account import CloudAccount, CloudProvider
from models.inventory_scan import InventoryScan
from models.user import User
from services.inventory import run_aws_inventory_scan, run_oci_inventory_scan

router = APIRouter()


@router.post("/aws/scan/{cloud_account_id}", response_model=InventoryScanRead)
def run_aws_scan(
    cloud_account_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.INVENTORY_SCAN)),
    db: Session = Depends(get_db),
) -> InventoryScan:
    cloud_account = db.scalar(
        select(CloudAccount).where(
            CloudAccount.id == cloud_account_id,
            CloudAccount.tenant_id == current_user.tenant_id,
            CloudAccount.provider == CloudProvider.AWS.value,
            CloudAccount.is_active.is_(True),
        )
    )
    if cloud_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cloud account not found")
    return run_aws_inventory_scan(db, cloud_account=cloud_account, current_user=current_user)


@router.post("/oci/scan/{cloud_account_id}", response_model=InventoryScanRead)
def run_oci_scan(
    cloud_account_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.INVENTORY_SCAN)),
    db: Session = Depends(get_db),
) -> InventoryScan:
    cloud_account = db.scalar(
        select(CloudAccount).where(
            CloudAccount.id == cloud_account_id,
            CloudAccount.tenant_id == current_user.tenant_id,
            CloudAccount.provider == CloudProvider.OCI.value,
            CloudAccount.is_active.is_(True),
        )
    )
    if cloud_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cloud account not found")
    return run_oci_inventory_scan(db, cloud_account=cloud_account, current_user=current_user)


@router.get("/scans/{scan_id}", response_model=InventoryScanRead)
def get_scan(
    scan_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.INVENTORY_READ)),
    db: Session = Depends(get_db),
) -> InventoryScan:
    scan = db.scalar(select(InventoryScan).where(InventoryScan.id == scan_id, InventoryScan.tenant_id == current_user.tenant_id))
    if scan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")
    return scan
