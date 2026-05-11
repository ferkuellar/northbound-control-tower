from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from findings.engine import FindingsEngine, FindingsRunSummary
from findings.enums import CloudProvider, FindingStatus
from models.cloud_account import CloudAccount
from models.finding import Finding
from models.user import User
from services.audit_log import create_audit_log

logger = logging.getLogger(__name__)


def run_findings(
    db: Session,
    *,
    current_user: User,
    cloud_account_id: uuid.UUID | None = None,
    provider: str | None = None,
) -> FindingsRunSummary:
    normalized_provider = _validate_provider(provider)
    if cloud_account_id:
        cloud_account = db.scalar(
            select(CloudAccount).where(
                CloudAccount.id == cloud_account_id,
                CloudAccount.tenant_id == current_user.tenant_id,
                CloudAccount.is_active.is_(True),
            )
        )
        if cloud_account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cloud account not found")
        if normalized_provider and cloud_account.provider != normalized_provider:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cloud account provider mismatch")
        normalized_provider = normalized_provider or cloud_account.provider

    logger.info(
        "Findings run started",
        extra={
            "tenant_id": str(current_user.tenant_id),
            "cloud_account_id": str(cloud_account_id) if cloud_account_id else None,
            "provider": normalized_provider,
        },
    )
    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="findings_run_started",
        resource_type="finding",
        metadata={"cloud_account_id": str(cloud_account_id) if cloud_account_id else None, "provider": normalized_provider},
    )
    try:
        summary = FindingsEngine(db).run(
            tenant_id=current_user.tenant_id,
            cloud_account_id=cloud_account_id,
            provider=normalized_provider,
        )
        create_audit_log(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="findings_run_completed",
            resource_type="finding",
            metadata={
                "cloud_account_id": str(cloud_account_id) if cloud_account_id else None,
                "provider": normalized_provider,
                "resources_evaluated": summary.resources_evaluated,
                "findings_created": summary.findings_created,
                "findings_updated": summary.findings_updated,
                "rule_errors": summary.rule_errors,
            },
        )
        db.commit()
        logger.info(
            "Findings run completed",
            extra={
                "tenant_id": str(current_user.tenant_id),
                "cloud_account_id": str(cloud_account_id) if cloud_account_id else None,
                "provider": normalized_provider,
                "resources_evaluated": summary.resources_evaluated,
                "findings_created": summary.findings_created,
                "findings_updated": summary.findings_updated,
                "rule_errors": summary.rule_errors,
            },
        )
        return summary
    except Exception as exc:
        db.rollback()
        create_audit_log(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="findings_run_failed",
            resource_type="finding",
            metadata={"cloud_account_id": str(cloud_account_id) if cloud_account_id else None, "provider": normalized_provider, "error": str(exc)},
        )
        db.commit()
        logger.exception(
            "Findings run failed",
            extra={
                "tenant_id": str(current_user.tenant_id),
                "cloud_account_id": str(cloud_account_id) if cloud_account_id else None,
                "provider": normalized_provider,
            },
        )
        raise


def update_finding_status(
    db: Session,
    *,
    current_user: User,
    finding_id: uuid.UUID,
    new_status: FindingStatus,
) -> Finding:
    finding = db.scalar(select(Finding).where(Finding.id == finding_id, Finding.tenant_id == current_user.tenant_id))
    if finding is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    finding.status = new_status.value
    finding.resolved_at = datetime.now(UTC) if new_status == FindingStatus.RESOLVED else None
    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="finding_status_updated",
        resource_type="finding",
        resource_id=str(finding.id),
        metadata={"status": finding.status},
    )
    db.commit()
    db.refresh(finding)
    return finding


def finding_summary(db: Session, *, tenant_id: uuid.UUID) -> dict[str, dict[str, int]]:
    return {
        "by_severity": _count_by(db, tenant_id=tenant_id, column=Finding.severity),
        "by_type": _count_by(db, tenant_id=tenant_id, column=Finding.finding_type),
        "by_category": _count_by(db, tenant_id=tenant_id, column=Finding.category),
        "by_provider": _count_by(db, tenant_id=tenant_id, column=Finding.provider),
        "by_status": _count_by(db, tenant_id=tenant_id, column=Finding.status),
    }


def _count_by(db: Session, *, tenant_id: uuid.UUID, column) -> dict[str, int]:
    rows = db.execute(select(column, func.count()).where(Finding.tenant_id == tenant_id).group_by(column)).all()
    return {str(key): int(count) for key, count in rows}


def _validate_provider(provider: str | None) -> str | None:
    if provider is None:
        return None
    try:
        return CloudProvider(provider).value
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider") from None
