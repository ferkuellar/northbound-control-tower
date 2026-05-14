import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth.guards import require_permission
from auth.permissions import Permission
from core.database import get_db
from models.user import User
from scoring.enums import ScoreType
from scoring.schemas import (
    ScoreCalculateRequest,
    ScoreCalculateResponse,
    ScoreHistoryResponse,
    ScoreLatestResponse,
    ScoreSummaryResponse,
)
from scoring.service import calculate_scores, latest_scores, score_history, score_summary

router = APIRouter()


@router.post("/calculate", response_model=ScoreCalculateResponse)
def calculate_scores_endpoint(
    payload: ScoreCalculateRequest,
    current_user: User = Depends(require_permission(Permission.SCORES_CALCULATE)),
    db: Session = Depends(get_db),
) -> ScoreCalculateResponse:
    result = calculate_scores(
        db,
        current_user=current_user,
        cloud_account_id=payload.cloud_account_id,
        provider=payload.provider,
    )
    return ScoreCalculateResponse(
        tenant_id=result.tenant_id,
        cloud_account_id=result.cloud_account_id,
        provider=result.provider,
        scores=result.scores,
        execution_time_ms=result.execution_time_ms,
    )


@router.get("/latest", response_model=ScoreLatestResponse)
def get_latest_scores(
    provider: str | None = None,
    cloud_account_id: uuid.UUID | None = None,
    current_user: User = Depends(require_permission(Permission.SCORES_READ)),
    db: Session = Depends(get_db),
) -> ScoreLatestResponse:
    return ScoreLatestResponse(
        items=latest_scores(db, tenant_id=current_user.tenant_id, provider=provider, cloud_account_id=cloud_account_id)
    )


@router.get("/history", response_model=ScoreHistoryResponse)
def get_score_history(
    score_type: ScoreType | None = None,
    provider: str | None = None,
    cloud_account_id: uuid.UUID | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_permission(Permission.SCORES_READ)),
    db: Session = Depends(get_db),
) -> ScoreHistoryResponse:
    items = score_history(
        db,
        tenant_id=current_user.tenant_id,
        score_type=score_type,
        provider=provider,
        cloud_account_id=cloud_account_id,
        limit=limit,
    )
    return ScoreHistoryResponse(items=items, total=len(items))


@router.get("/summary", response_model=ScoreSummaryResponse)
def get_score_summary(
    provider: str | None = None,
    cloud_account_id: uuid.UUID | None = None,
    current_user: User = Depends(require_permission(Permission.SCORES_READ)),
    db: Session = Depends(get_db),
) -> ScoreSummaryResponse:
    return ScoreSummaryResponse(**score_summary(db, tenant_id=current_user.tenant_id, provider=provider, cloud_account_id=cloud_account_id))
