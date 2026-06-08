from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.guards import require_permission
from auth.permissions import Permission
from core.database import get_db
from models.finding import Finding
from models.user import User
from provisioning.schemas import (
    ProvisioningArtifactListResponse,
    ProvisioningArtifactRead,
    ProvisioningRequestCreateFromFinding,
    ProvisioningRequestListResponse,
    ProvisioningRequestRead,
    ProvisioningTemplateRead,
)
from provisioning.service import ProvisioningRequestService
from provisioning.template_catalog import TEMPLATE_CATALOG
from services.audit_log import create_audit_log

router = APIRouter()


@router.get("/templates", response_model=list[ProvisioningTemplateRead])
def list_templates(
    current_user: User = Depends(require_permission(Permission.FINDINGS_READ)),
) -> list[ProvisioningTemplateRead]:
    return [
        ProvisioningTemplateRead(
            key=template.key,
            provider=template.provider,
            finding_types=list(template.finding_types),
            title=template.title,
            description=template.description,
            risk_level=template.risk_level,
            required_variables=list(template.required_variables),
            module_path=template.module_path,
        )
        for template in TEMPLATE_CATALOG.values()
    ]


@router.post("/requests/from-finding", response_model=ProvisioningRequestRead, status_code=status.HTTP_201_CREATED)
def create_request_from_finding(
    payload: ProvisioningRequestCreateFromFinding,
    current_user: User = Depends(require_permission(Permission.FINDINGS_WRITE)),
    db: Session = Depends(get_db),
) -> ProvisioningRequestRead:
    finding = db.scalar(select(Finding).where(Finding.id == payload.finding_id, Finding.tenant_id == current_user.tenant_id))
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    request = ProvisioningRequestService(db).create_from_finding(finding=finding, current_user=current_user)
    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="provisioning_request_created",
        resource_type="provisioning_request",
        resource_id=str(request.id),
        metadata={"request_number": request.request_number, "finding_id": str(finding.id), "template_key": request.template_key},
        commit=True,
    )
    return ProvisioningRequestRead.model_validate(request)


@router.get("/requests", response_model=ProvisioningRequestListResponse)
def list_requests(
    current_user: User = Depends(require_permission(Permission.FINDINGS_READ)),
    db: Session = Depends(get_db),
) -> ProvisioningRequestListResponse:
    requests = ProvisioningRequestService(db).list_requests(tenant_id=current_user.tenant_id)
    return ProvisioningRequestListResponse(items=[ProvisioningRequestRead.model_validate(item) for item in requests], total=len(requests))


@router.get("/requests/{request_id}", response_model=ProvisioningRequestRead)
def get_request(
    request_id: str,
    current_user: User = Depends(require_permission(Permission.FINDINGS_READ)),
    db: Session = Depends(get_db),
) -> ProvisioningRequestRead:
    request = ProvisioningRequestService(db).get_by_number_or_id(tenant_id=current_user.tenant_id, identifier=request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provisioning request not found")
    return ProvisioningRequestRead.model_validate(request)


@router.get("/requests/{request_id}/artifacts", response_model=ProvisioningArtifactListResponse)
def list_request_artifacts(
    request_id: str,
    current_user: User = Depends(require_permission(Permission.FINDINGS_READ)),
    db: Session = Depends(get_db),
) -> ProvisioningArtifactListResponse:
    request = ProvisioningRequestService(db).get_by_number_or_id(tenant_id=current_user.tenant_id, identifier=request_id)
    if request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provisioning request not found")
    artifacts = ProvisioningRequestService(db).list_artifacts(request=request)
    return ProvisioningArtifactListResponse(
        items=[ProvisioningArtifactRead.model_validate(artifact) for artifact in artifacts],
        total=len(artifacts),
    )
