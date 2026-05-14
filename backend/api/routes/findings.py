import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.guards import require_permission
from auth.permissions import Permission
from core.database import get_db
from findings.enums import FindingCategory, FindingSeverity, FindingStatus, FindingType
from findings.schemas import (
    FindingListResponse,
    FindingRead,
    FindingRunRequest,
    FindingRunResponse,
    FindingStatusUpdate,
    FindingSummaryResponse,
)
from findings.service import finding_summary, run_findings, update_finding_status
from models.finding import Finding
from models.user import User

router = APIRouter()


@router.post("/run", response_model=FindingRunResponse)
def run_findings_endpoint(
    payload: FindingRunRequest,
    current_user: User = Depends(require_permission(Permission.FINDINGS_WRITE)),
    db: Session = Depends(get_db),
) -> FindingRunResponse:
    summary = run_findings(
        db,
        current_user=current_user,
        cloud_account_id=payload.cloud_account_id,
        provider=payload.provider,
    )
    return FindingRunResponse(**summary.__dict__)


@router.get("", response_model=FindingListResponse)
def list_findings(
    provider: str | None = None,
    cloud_account_id: uuid.UUID | None = None,
    finding_type: FindingType | None = None,
    severity: FindingSeverity | None = None,
    status_filter: FindingStatus | None = Query(default=None, alias="status"),
    category: FindingCategory | None = None,
    current_user: User = Depends(require_permission(Permission.FINDINGS_READ)),
    db: Session = Depends(get_db),
) -> FindingListResponse:
    statement = select(Finding).where(Finding.tenant_id == current_user.tenant_id)
    if provider:
        statement = statement.where(Finding.provider == provider)
    if cloud_account_id:
        statement = statement.where(Finding.cloud_account_id == cloud_account_id)
    if finding_type:
        statement = statement.where(Finding.finding_type == finding_type.value)
    if severity:
        statement = statement.where(Finding.severity == severity.value)
    if status_filter:
        statement = statement.where(Finding.status == status_filter.value)
    if category:
        statement = statement.where(Finding.category == category.value)
    items = list(db.scalars(statement.order_by(Finding.last_seen_at.desc())))
    return FindingListResponse(items=items, total=len(items))


@router.get("/summary", response_model=FindingSummaryResponse)
def get_findings_summary(
    current_user: User = Depends(require_permission(Permission.FINDINGS_READ)),
    db: Session = Depends(get_db),
) -> FindingSummaryResponse:
    return FindingSummaryResponse(**finding_summary(db, tenant_id=current_user.tenant_id))


@router.get("/{finding_id}", response_model=FindingRead)
def get_finding(
    finding_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.FINDINGS_READ)),
    db: Session = Depends(get_db),
) -> Finding:
    finding = db.scalar(select(Finding).where(Finding.id == finding_id, Finding.tenant_id == current_user.tenant_id))
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return finding


@router.patch("/{finding_id}/status", response_model=FindingRead)
def patch_finding_status(
    finding_id: uuid.UUID,
    payload: FindingStatusUpdate,
    current_user: User = Depends(require_permission(Permission.FINDINGS_WRITE)),
    db: Session = Depends(get_db),
) -> Finding:
    return update_finding_status(db, current_user=current_user, finding_id=finding_id, new_status=payload.status)
