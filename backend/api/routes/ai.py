import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ai.errors import AIAnalysisError
from ai.schemas import AIAnalysisListResponse, AIAnalysisRead, AIAnalysisRequest, AIAnalysisResponse, AIContextPreview, AIProviderStatus
from ai.service import AIAnalysisService, get_analysis, list_analyses, provider_statuses
from auth.dependencies import get_current_user, require_roles
from core.config import settings
from core.database import get_db
from models.user import User, UserRole
from services.audit_log import create_audit_log

router = APIRouter()


@router.get("/providers", response_model=list[AIProviderStatus])
def get_ai_providers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AIProviderStatus]:
    statuses = provider_statuses()
    create_audit_log(
        db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        action="ai_provider_health_checked",
        resource_type="ai_provider",
        metadata={"providers": [status.provider.value for status in statuses]},
        commit=True,
    )
    return statuses


@router.get("/context-preview", response_model=AIContextPreview)
def get_context_preview(
    cloud_account_id: uuid.UUID | None = Query(default=None),
    cloud_provider: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIContextPreview:
    context = AIAnalysisService(db).context_preview(
        current_user=current_user,
        cloud_account_id=cloud_account_id,
        cloud_provider=cloud_provider,
    )
    return AIContextPreview(
        context=context,
        limits={
            "max_findings": settings.ai_max_input_findings,
            "max_resources": settings.ai_max_input_resources,
        },
    )


@router.post("/analyze", response_model=AIAnalysisResponse, status_code=status.HTTP_201_CREATED)
def analyze(
    payload: AIAnalysisRequest,
    current_user: User = Depends(require_roles([UserRole.ADMIN, UserRole.ANALYST])),
    db: Session = Depends(get_db),
) -> AIAnalysisResponse:
    try:
        analysis = AIAnalysisService(db).generate(current_user=current_user, request=payload)
    except AIAnalysisError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AIAnalysisResponse(analysis=AIAnalysisRead.model_validate(analysis))


@router.get("/analyses", response_model=AIAnalysisListResponse)
def get_analyses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIAnalysisListResponse:
    items = list_analyses(db, tenant_id=current_user.tenant_id)
    return AIAnalysisListResponse(items=items, total=len(items))


@router.get("/analyses/{analysis_id}", response_model=AIAnalysisRead)
def get_analysis_detail(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AIAnalysisRead:
    analysis = get_analysis(db, tenant_id=current_user.tenant_id, analysis_id=analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI analysis not found")
    return AIAnalysisRead.model_validate(analysis)
