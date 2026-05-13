from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.report_artifact import ReportArtifact
from models.user import User
from reports.branding import merge_branding
from reports.context_builder import ReportContextBuilder
from reports.enums import ReportFormat, ReportStatus, ReportType
from reports.errors import ReportingError, ReportValidationError
from reports.html_renderer import HTMLReportRenderer
from reports.pdf_renderer import PDFReportRenderer
from reports.schemas import ReportGenerateRequest
from reports.validators import validate_report_html
from services.audit_log import create_audit_log


class ReportingService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.html_renderer = HTMLReportRenderer()
        self.pdf_renderer = PDFReportRenderer()

    def generate(self, *, current_user: User, request: ReportGenerateRequest) -> ReportArtifact:
        started = time.perf_counter()
        title = self._title(request.report_type)
        branding = merge_branding(request.branding)
        create_audit_log(
            self.db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="report_generation_started",
            resource_type="report",
            metadata={
                "report_type": request.report_type.value,
                "report_format": request.report_format.value,
                "provider": request.provider,
            },
        )
        try:
            context = ReportContextBuilder(self.db).build(
                tenant_id=current_user.tenant_id,
                report_type=request.report_type,
                provider=request.provider,
                cloud_account_id=request.cloud_account_id,
            )
            html = self.html_renderer.render(report_type=request.report_type, context=context, branding=branding, title=title)
            validate_report_html(title=title, html=html, report_type=request.report_type)

            report = ReportArtifact(
                tenant_id=current_user.tenant_id,
                cloud_account_id=request.cloud_account_id,
                provider=request.provider,
                report_type=request.report_type.value,
                report_format=request.report_format.value,
                status=ReportStatus.PENDING.value,
                title=title,
                generated_by_user_id=current_user.id,
                branding=branding.as_template_data(),
                metadata_json={
                    "resource_count": context["inventory_summary"]["total_resources"],
                    "finding_count": context["findings_summary"]["total"],
                    "ai_analysis_available": context["ai"]["available"],
                    "generation_time_ms": 0,
                },
                html_content=html,
            )
            self.db.add(report)
            self.db.flush()

            if request.report_format == ReportFormat.PDF:
                pdf_metadata = self.pdf_renderer.render_to_file(html=html, tenant_id=current_user.tenant_id, report_id=report.id)
                report.storage_path = str(pdf_metadata["storage_path"])
                report.file_size_bytes = int(pdf_metadata["file_size_bytes"])
                report.checksum = str(pdf_metadata["checksum"])
            else:
                report.file_size_bytes = len(html.encode("utf-8"))

            report.status = ReportStatus.GENERATED.value
            report.generated_at = datetime.now(UTC)
            report.metadata_json = {**report.metadata_json, "generation_time_ms": int((time.perf_counter() - started) * 1000)}
            create_audit_log(
                self.db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                action="report_generation_completed",
                resource_type="report",
                resource_id=str(report.id),
                metadata={
                    "report_type": request.report_type.value,
                    "report_format": request.report_format.value,
                    "provider": request.provider,
                    "generation_time_ms": report.metadata_json["generation_time_ms"],
                },
            )
            self.db.commit()
            self.db.refresh(report)
            return report
        except (ReportValidationError, ReportingError, ValueError) as exc:
            self.db.rollback()
            create_audit_log(
                self.db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                action="report_generation_failed",
                resource_type="report",
                metadata={
                    "report_type": request.report_type.value,
                    "report_format": request.report_format.value,
                    "provider": request.provider,
                    "error": str(exc),
                    "generation_time_ms": int((time.perf_counter() - started) * 1000),
                },
                commit=True,
            )
            raise ReportingError(str(exc)) from exc

    def _title(self, report_type: ReportType) -> str:
        if report_type == ReportType.EXECUTIVE:
            return "Northbound Executive Cloud Operations Report"
        return "Northbound Technical Cloud Assessment Report"


def list_reports(db: Session, *, tenant_id: uuid.UUID) -> list[ReportArtifact]:
    return list(db.scalars(select(ReportArtifact).where(ReportArtifact.tenant_id == tenant_id).order_by(ReportArtifact.created_at.desc())))


def get_report(db: Session, *, tenant_id: uuid.UUID, report_id: uuid.UUID) -> ReportArtifact | None:
    return db.scalar(select(ReportArtifact).where(ReportArtifact.id == report_id, ReportArtifact.tenant_id == tenant_id))


def safe_report_path(report: ReportArtifact) -> Path | None:
    if not report.storage_path:
        return None
    path = Path(report.storage_path)
    if ".." in path.parts:
        return None
    return path
