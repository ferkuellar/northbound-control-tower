from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from findings.enums import FindingCategory, FindingSeverity, FindingStatus, FindingType


@dataclass(frozen=True)
class FindingCandidate:
    title: str
    description: str
    evidence: dict[str, Any]
    recommendation: str
    estimated_monthly_waste: float | None = None


class FindingRunRequest(BaseModel):
    cloud_account_id: uuid.UUID | None = None
    provider: str | None = None


class FindingRunResponse(BaseModel):
    scan_id: uuid.UUID | None = None
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID | None = None
    provider: str | None = None
    resources_evaluated: int
    findings_created: int
    findings_updated: int
    findings_by_type: dict[str, int]
    findings_by_severity: dict[str, int]
    rule_errors: int
    execution_time_ms: int


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID
    resource_id: uuid.UUID | None
    provider: str
    finding_type: FindingType
    category: FindingCategory
    severity: FindingSeverity
    status: FindingStatus
    title: str
    description: str
    evidence: dict[str, Any]
    recommendation: str
    estimated_monthly_waste: float | None
    rule_id: str
    fingerprint: str
    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class FindingListResponse(BaseModel):
    items: list[FindingRead]
    total: int


class FindingStatusUpdate(BaseModel):
    status: FindingStatus


class FindingSummaryResponse(BaseModel):
    by_severity: dict[str, int]
    by_type: dict[str, int]
    by_category: dict[str, int]
    by_provider: dict[str, int]
    by_status: dict[str, int]
