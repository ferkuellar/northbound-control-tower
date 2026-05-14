from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from models.tenant import Tenant


class CostOptimizationCase(Base, TimestampMixin):
    __tablename__ = "cost_optimization_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    monthly_spend: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)

    tenant: Mapped["Tenant"] = relationship()
    service_breakdown: Mapped[list["CostServiceBreakdown"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["CostRecommendation"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class CostServiceBreakdown(Base, TimestampMixin):
    __tablename__ = "cost_service_breakdowns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_optimization_cases.id"), nullable=False, index=True
    )
    service_name: Mapped[str] = mapped_column(String(80), nullable=False)
    monthly_cost: Mapped[float] = mapped_column(Float, nullable=False)
    percentage: Mapped[float] = mapped_column(Float, nullable=False)

    case: Mapped["CostOptimizationCase"] = relationship(back_populates="service_breakdown")


class CostRecommendation(Base, TimestampMixin):
    __tablename__ = "cost_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cost_optimization_cases.id"), nullable=False, index=True
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    service_name: Mapped[str] = mapped_column(String(80), nullable=False)
    estimated_savings_percent: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_monthly_savings: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_annual_savings: Mapped[float] = mapped_column(Float, nullable=False)
    implementation_effort: Mapped[str] = mapped_column(String(60), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(60), nullable=False)
    assumptions: Mapped[str] = mapped_column(String(2000), nullable=False)

    case: Mapped["CostOptimizationCase"] = relationship(back_populates="recommendations")
