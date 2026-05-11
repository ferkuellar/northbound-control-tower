from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from ai.enums import AIAnalysisStatus, AIAnalysisType, AIProvider


class AIAnalysisRequest(BaseModel):
    analysis_type: AIAnalysisType = AIAnalysisType.FULL_ASSESSMENT
    provider: AIProvider | None = None
    cloud_account_id: uuid.UUID | None = None
    cloud_provider: str | None = None


class AIProviderStatus(BaseModel):
    provider: AIProvider
    configured: bool
    enabled: bool
    model_name: str | None = None
    base_url: str | None = None
    message: str


class AIContextPreview(BaseModel):
    context: dict[str, Any]
    limits: dict[str, int]
    sanitized: bool = True


class AIAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID | None
    provider: str | None
    ai_provider: AIProvider
    analysis_type: AIAnalysisType
    status: AIAnalysisStatus
    input_summary: dict[str, Any]
    output: dict[str, Any]
    raw_text: str | None
    error_message: str | None
    model_name: str | None
    prompt_version: str
    created_by_user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class AIAnalysisResponse(BaseModel):
    analysis: AIAnalysisRead


class AIAnalysisListResponse(BaseModel):
    items: list[AIAnalysisRead]
    total: int
