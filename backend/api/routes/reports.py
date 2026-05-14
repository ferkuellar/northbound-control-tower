import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.orm import Session

from auth.guards import require_permission
from auth.permissions import Permission
from core.database import get_db
from models.user import User
from reports.enums import ReportFormat, ReportStatus
from reports.errors import ReportingError
from reports.schemas import ReportArtifactRead, ReportGenerateRequest, ReportGenerateResponse, ReportListResponse
from reports.service import ReportingService, get_report, list_reports, safe_report_path
from services.audit_log import create_audit_log

router = APIRouter()


@router.post("/generate", response_model=ReportGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_report(
    payload: ReportGenerateRequest,
    current_user: User = Depends(require_permission(Permission.REPORTS_GENERATE)),
    db: Session = Depends(get_db),
) -> ReportGenerateResponse:
    try:
        report = ReportingService(db).generate(current_user=current_user, request=payload)
    except ReportingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ReportGenerateResponse(report=ReportArtifactRead.model_validate(report))


@router.get("", response_model=ReportListResponse)
def get_reports(
    tenant_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require_permission(Permission.REPORTS_READ)),
    db: Session = Depends(get_db),
) -> ReportListResponse:
    scoped_tenant_id = tenant_id or current_user.tenant_id
    if current_user.role != "ADMIN" and scoped_tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")
    items = list_reports(db, tenant_id=scoped_tenant_id)
    return ReportListResponse(items=items, total=len(items))


@router.get("/{report_id}", response_model=ReportArtifactRead)
def get_report_metadata(
    report_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.REPORTS_READ)),
    db: Session = Depends(get_db),
) -> ReportArtifactRead:
    report = get_report(db, tenant_id=current_user.tenant_id, report_id=report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportArtifactRead.model_validate(report)


@router.get("/{report_id}/preview", response_class=HTMLResponse)
def preview_report(
    report_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.REPORTS_READ)),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    report = get_report(db, tenant_id=current_user.tenant_id, report_id=report_id)
    if report is None or report.status != ReportStatus.GENERATED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if not report.html_content:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report preview is unavailable")
    return HTMLResponse(content=report.html_content)


@router.get("/{report_id}/download")
def download_report(
    report_id: uuid.UUID,
    current_user: User = Depends(require_permission(Permission.REPORTS_READ)),
    db: Session = Depends(get_db),
) -> Response:
    report = get_report(db, tenant_id=current_user.tenant_id, report_id=report_id)
    if report is None or report.status != ReportStatus.GENERATED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="report_downloaded",
        resource_type="report",
        resource_id=str(report.id),
        metadata={"report_type": report.report_type, "report_format": report.report_format, "provider": report.provider},
        commit=True,
    )

    filename = f"{report.report_type}-{report.id}.{report.report_format}"
    if report.report_format == ReportFormat.HTML.value:
        return HTMLResponse(content=report.html_content or "", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

    path = safe_report_path(report)
    if path is None or not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file is unavailable")
    return FileResponse(path=path, media_type="application/pdf", filename=filename)
