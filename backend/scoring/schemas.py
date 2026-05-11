from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from scoring.enums import ScoreGrade, ScoreTrend, ScoreType


class ScoreCalculateRequest(BaseModel):
    cloud_account_id: uuid.UUID | None = None
    provider: str | None = None


class CloudScoreRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID | None
    provider: str | None
    score_type: ScoreType
    score_value: int
    grade: ScoreGrade
    trend: ScoreTrend
    summary: str
    evidence: dict[str, Any]
    calculated_at: datetime
    created_at: datetime
    updated_at: datetime


class ScoreCalculateResponse(BaseModel):
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID | None
    provider: str | None
    scores: list[CloudScoreRead]
    execution_time_ms: int


class ScoreLatestResponse(BaseModel):
    items: list[CloudScoreRead]


class ScoreHistoryResponse(BaseModel):
    items: list[CloudScoreRead]
    total: int


class ScoreSummaryResponse(BaseModel):
    overall_score: int | None
    domain_scores: dict[str, int]
    grades: dict[str, str]
    trends: dict[str, str]
    top_drivers: list[dict[str, Any]]
    counts_by_severity: dict[str, int]
