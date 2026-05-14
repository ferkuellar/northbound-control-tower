from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CostServiceBreakdownRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_name: str
    monthly_cost: float
    percentage: float


class CostRecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    priority: int
    title: str
    description: str
    service_name: str
    estimated_savings_percent: float
    estimated_monthly_savings: float
    estimated_annual_savings: float
    implementation_effort: str
    risk_level: str
    assumptions: str


class CostOptimizationCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    provider: str
    monthly_spend: float
    currency: str
    description: str
    created_at: datetime
    updated_at: datetime
    service_breakdown: list[CostServiceBreakdownRead]
    recommendations: list[CostRecommendationRead]


class CostOptimizationResponse(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    case: CostOptimizationCaseRead
    estimated_monthly_savings: float
    estimated_annual_savings: float
    optimized_monthly_cost: float
    architecture_current: list[str]
    architecture_proposed: list[str]
    implementation_plan: list[str]
