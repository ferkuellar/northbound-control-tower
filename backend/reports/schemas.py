from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from reports.enums import ReportFormat, ReportStatus, ReportType


class ReportGenerateRequest(BaseModel):
    report_type: ReportType
    report_format: ReportFormat
    provider: str | None = Field(default=None, max_length=30)
    cloud_account_id: uuid.UUID | None = None
    branding: dict[str, Any] | None = None


class ReportArtifactRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID | None
    provider: str | None
    report_type: ReportType
    report_format: ReportFormat
    status: ReportStatus
    title: str
    generated_by_user_id: uuid.UUID | None
    branding: dict[str, Any]
    metadata_json: dict[str, Any]
    storage_path: str | None
    file_size_bytes: int | None
    checksum: str | None
    created_at: datetime
    updated_at: datetime
    generated_at: datetime | None


class ReportGenerateResponse(BaseModel):
    report: ReportArtifactRead


class ReportListResponse(BaseModel):
    items: list[ReportArtifactRead]
    total: int
