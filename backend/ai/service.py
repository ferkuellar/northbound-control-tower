from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.context_builder import AIContextBuilder
from ai.enums import AIAnalysisStatus, AIProvider
from ai.errors import AIAnalysisError, AIOutputValidationError, AIProviderConfigurationError
from ai.prompts import PROMPT_VERSION, build_prompt
from ai.provider import get_ai_provider
from ai.schemas import AIAnalysisRequest, AIProviderStatus
from ai.validators import validate_ai_output
from core.config import settings
from models.ai_analysis import AIAnalysis
from models.user import User
from services.audit_log import create_audit_log


def provider_statuses() -> list[AIProviderStatus]:
    statuses: list[AIProviderStatus] = []
    for provider in (AIProvider.DEEPSEEK, AIProvider.CLAUDE, AIProvider.OPENAI):
        try:
            instance = get_ai_provider(provider)
            statuses.append(instance.health_check())
        except AIProviderConfigurationError as exc:
            statuses.append(
                AIProviderStatus(
                    provider=provider,
                    configured=False,
                    enabled=False,
                    model_name=_model_name(provider),
                    base_url=settings.deepseek_base_url if provider == AIProvider.DEEPSEEK else None,
                    message=str(exc),
                )
            )
    return statuses


def _model_name(provider: AIProvider) -> str:
    if provider == AIProvider.DEEPSEEK:
        return settings.deepseek_model
    if provider == AIProvider.CLAUDE:
        return settings.claude_model
    if provider == AIProvider.OPENAI:
        return settings.openai_model
    return ""


class AIAnalysisService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def context_preview(
        self,
        *,
        current_user: User,
        cloud_account_id: uuid.UUID | None = None,
        cloud_provider: str | None = None,
    ) -> dict:
        return AIContextBuilder(self.db).build(
            tenant_id=current_user.tenant_id,
            cloud_account_id=cloud_account_id,
            cloud_provider=cloud_provider,
        )

    def generate(self, *, current_user: User, request: AIAnalysisRequest) -> AIAnalysis:
        started = time.perf_counter()
        provider_name = request.provider or AIProvider(settings.ai_provider)
        analysis = AIAnalysis(
            tenant_id=current_user.tenant_id,
            cloud_account_id=request.cloud_account_id,
            provider=request.cloud_provider,
            ai_provider=provider_name.value,
            analysis_type=request.analysis_type.value,
            status=AIAnalysisStatus.PENDING.value,
            input_summary={},
            output={},
            model_name=None,
            prompt_version=PROMPT_VERSION,
            created_by_user_id=current_user.id,
        )
        self.db.add(analysis)
        self.db.flush()
        create_audit_log(
            self.db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="ai_analysis_started",
            resource_type="ai_analysis",
            resource_id=str(analysis.id),
            metadata={"provider": provider_name.value, "analysis_type": request.analysis_type.value},
        )

        try:
            provider = get_ai_provider(provider_name)
            context = self.context_preview(
                current_user=current_user,
                cloud_account_id=request.cloud_account_id,
                cloud_provider=request.cloud_provider,
            )
            prompt = build_prompt(request.analysis_type, context)
            raw_text = provider.generate_analysis(prompt, settings.ai_max_tokens, settings.ai_temperature)
            output = validate_ai_output(raw_text, context=context)
            analysis.status = AIAnalysisStatus.COMPLETED.value
            analysis.input_summary = context
            analysis.output = output
            analysis.raw_text = raw_text
            analysis.model_name = provider.model_name
            analysis.completed_at = datetime.now(UTC)
            create_audit_log(
                self.db,
                tenant_id=current_user.tenant_id,
                user_id=current_user.id,
                action="ai_analysis_completed",
                resource_type="ai_analysis",
                resource_id=str(analysis.id),
                metadata={
                    "provider": provider.provider_name,
                    "analysis_type": request.analysis_type.value,
                    "execution_time_ms": int((time.perf_counter() - started) * 1000),
                },
            )
        except (AIProviderConfigurationError, AIOutputValidationError, ValueError) as exc:
            self._fail_analysis(analysis, current_user=current_user, error=str(exc), started=started)
            raise AIAnalysisError(str(exc)) from exc
        except Exception as exc:
            self._fail_analysis(analysis, current_user=current_user, error="AI provider request failed", started=started)
            raise AIAnalysisError("AI provider request failed") from exc

        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def _fail_analysis(self, analysis: AIAnalysis, *, current_user: User, error: str, started: float) -> None:
        analysis.status = AIAnalysisStatus.FAILED.value
        analysis.error_message = error
        analysis.completed_at = datetime.now(UTC)
        create_audit_log(
            self.db,
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            action="ai_analysis_failed",
            resource_type="ai_analysis",
            resource_id=str(analysis.id),
            metadata={"error": error, "execution_time_ms": int((time.perf_counter() - started) * 1000)},
        )
        self.db.commit()
        self.db.refresh(analysis)


def list_analyses(db: Session, *, tenant_id: uuid.UUID) -> list[AIAnalysis]:
    return list(db.scalars(select(AIAnalysis).where(AIAnalysis.tenant_id == tenant_id).order_by(AIAnalysis.created_at.desc())))


def get_analysis(db: Session, *, tenant_id: uuid.UUID, analysis_id: uuid.UUID) -> AIAnalysis | None:
    return db.scalar(select(AIAnalysis).where(AIAnalysis.id == analysis_id, AIAnalysis.tenant_id == tenant_id))
