from __future__ import annotations

import logging
import time
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
from models.user import User
from observability.instruments import operation_span
from observability.metrics import SCORING_RUN_DURATION_SECONDS, SCORING_RUNS_TOTAL, provider_label
from scoring.engine import RiskScoringEngine, ScoreRunResult
from scoring.enums import ScoreType
from services.audit_log import create_audit_log

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {"aws", "oci"}


def calculate_scores(
    db: Session,
    *,
    current_user: User,
    cloud_account_id: uuid.UUID | None = None,
    provider: str | None = None,
) -> ScoreRunResult:
    started = time.perf_counter()
    normalized_provider = _validate_scope(db, tenant_id=current_user.tenant_id, cloud_account_id=cloud_account_id, provider=provider)
    logger.info(
        "Scoring calculation started",
        extra={"tenant_id": str(current_user.tenant_id), "cloud_account_id": str(cloud_account_id) if cloud_account_id else None, "provider": normalized_provider},
    )
    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="scoring_calculation_started",
        resource_type="cloud_score",
        metadata={"cloud_account_id": str(cloud_account_id) if cloud_account_id else None, "provider": normalized_provider},
    )
    try:
        with operation_span("scoring.calculate", provider=provider_label(normalized_provider), operation_name="score_calculation"):
            result = RiskScoringEngine(db).calculate(
                tenant_id=current_user.tenant_id,
                cloud_account_id=cloud_account_id,
                provider=normalized_provider,
            )
        create_audit_log(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="scoring_calculation_completed",
            resource_type="cloud_score",
            metadata={
                "cloud_account_id": str(cloud_account_id) if cloud_account_id else None,
                "provider": normalized_provider,
                "score_types_calculated": [score.score_type for score in result.scores],
                "execution_time_ms": result.execution_time_ms,
            },
        )
        db.commit()
        for score in result.scores:
            db.refresh(score)
        metric_provider = provider_label(normalized_provider)
        SCORING_RUNS_TOTAL.labels(provider=metric_provider, status="completed").inc()
        SCORING_RUN_DURATION_SECONDS.labels(provider=metric_provider, status="completed").observe(time.perf_counter() - started)
        logger.info(
            "Scoring calculation completed",
            extra={
                "tenant_id": str(current_user.tenant_id),
                "cloud_account_id": str(cloud_account_id) if cloud_account_id else None,
                "provider": normalized_provider,
                "score_types_calculated": [score.score_type for score in result.scores],
                "execution_time_ms": result.execution_time_ms,
            },
        )
        return result
    except Exception as exc:
        db.rollback()
        create_audit_log(
            db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="scoring_calculation_failed",
            resource_type="cloud_score",
            metadata={"cloud_account_id": str(cloud_account_id) if cloud_account_id else None, "provider": normalized_provider, "error": str(exc)},
        )
        db.commit()
        metric_provider = provider_label(normalized_provider)
        SCORING_RUNS_TOTAL.labels(provider=metric_provider, status="failed").inc()
        SCORING_RUN_DURATION_SECONDS.labels(provider=metric_provider, status="failed").observe(time.perf_counter() - started)
        logger.exception(
            "Scoring calculation failed",
            extra={"tenant_id": str(current_user.tenant_id), "cloud_account_id": str(cloud_account_id) if cloud_account_id else None, "provider": normalized_provider},
        )
        raise


def latest_scores(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    cloud_account_id: uuid.UUID | None = None,
    provider: str | None = None,
) -> list[CloudScore]:
    statement = select(CloudScore).where(CloudScore.tenant_id == tenant_id)
    if cloud_account_id:
        statement = statement.where(CloudScore.cloud_account_id == cloud_account_id)
    if provider:
        statement = statement.where(CloudScore.provider == provider)
    scores = list(db.scalars(statement.order_by(CloudScore.calculated_at.desc())))
    latest: dict[tuple[str, str | None, str | None], CloudScore] = {}
    for score in scores:
        key = (score.score_type, str(score.cloud_account_id) if score.cloud_account_id else None, score.provider)
        latest.setdefault(key, score)
    return list(latest.values())


def score_history(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    score_type: ScoreType | None = None,
    provider: str | None = None,
    cloud_account_id: uuid.UUID | None = None,
    limit: int = 50,
) -> list[CloudScore]:
    statement = select(CloudScore).where(CloudScore.tenant_id == tenant_id)
    if score_type:
        statement = statement.where(CloudScore.score_type == score_type.value)
    if provider:
        statement = statement.where(CloudScore.provider == provider)
    if cloud_account_id:
        statement = statement.where(CloudScore.cloud_account_id == cloud_account_id)
    return list(db.scalars(statement.order_by(CloudScore.calculated_at.desc()).limit(limit)))


def score_summary(db: Session, *, tenant_id: uuid.UUID, provider: str | None = None, cloud_account_id: uuid.UUID | None = None) -> dict:
    scores = latest_scores(db, tenant_id=tenant_id, provider=provider, cloud_account_id=cloud_account_id)
    by_type = {score.score_type: score for score in scores}
    overall = by_type.get(ScoreType.OVERALL.value)
    domain_scores = {key: score.score_value for key, score in by_type.items() if key != ScoreType.OVERALL.value}
    grades = {key: score.grade for key, score in by_type.items()}
    trends = {key: score.trend for key, score in by_type.items()}
    counts_by_severity = overall.evidence.get("findings_by_severity", {}) if overall else {}
    top_drivers = overall.evidence.get("top_drivers", []) if overall else []
    return {
        "overall_score": overall.score_value if overall else None,
        "domain_scores": domain_scores,
        "grades": grades,
        "trends": trends,
        "top_drivers": top_drivers,
        "counts_by_severity": counts_by_severity,
    }


def _validate_scope(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    cloud_account_id: uuid.UUID | None,
    provider: str | None,
) -> str | None:
    if provider and provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported provider")
    if cloud_account_id:
        cloud_account = db.scalar(
            select(CloudAccount).where(
                CloudAccount.id == cloud_account_id,
                CloudAccount.tenant_id == tenant_id,
                CloudAccount.is_active.is_(True),
            )
        )
        if cloud_account is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cloud account not found")
        if provider and provider != cloud_account.provider:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cloud account provider mismatch")
        return cloud_account.provider
    return provider
