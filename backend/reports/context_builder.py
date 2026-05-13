from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.ai_analysis import AIAnalysis
from models.cloud_score import CloudScore
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant
from reports.enums import ReportType

SECRET_KEYWORDS = ("secret", "password", "private_key", "passphrase", "token", "api_key", "access_key", "fingerprint")


def sanitize_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return "[truncated]"
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(secret in lowered for secret in SECRET_KEYWORDS):
                continue
            cleaned[str(key)] = sanitize_value(item, depth=depth + 1)
        return cleaned
    if isinstance(value, list):
        return [sanitize_value(item, depth=depth + 1) for item in value[:25]]
    if isinstance(value, str):
        if any(marker in value for marker in ("-----BEGIN", "AKIA", "ASIA", "Bearer ", "sk-")):
            return "[redacted]"
        return value[:1200]
    return value


def _count_by(items: list[Any], attr: str) -> dict[str, int]:
    return dict(Counter(str(getattr(item, attr) or "unknown") for item in items))


class ReportContextBuilder:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(
        self,
        *,
        tenant_id: uuid.UUID,
        report_type: ReportType,
        provider: str | None = None,
        cloud_account_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        tenant = self.db.get(Tenant, tenant_id)
        resources = self._resources(tenant_id, provider=provider, cloud_account_id=cloud_account_id)
        findings = self._findings(tenant_id, provider=provider, cloud_account_id=cloud_account_id)
        scores = self._scores(tenant_id, provider=provider, cloud_account_id=cloud_account_id)
        ai_analysis = self._latest_ai_analysis(tenant_id, report_type=report_type, provider=provider, cloud_account_id=cloud_account_id)

        score_map: dict[str, int] = {}
        for score in scores:
            score_map.setdefault(score.score_type, score.score_value)

        top_findings = findings[:10]
        detailed_findings = findings[:50] if report_type == ReportType.TECHNICAL else top_findings

        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "tenant": {"id": str(tenant_id), "name": tenant.name if tenant else "unknown"},
            "scope": {"provider": provider or "all", "cloud_account_id": str(cloud_account_id) if cloud_account_id else None},
            "report_type": report_type.value,
            "scores": score_map,
            "findings_summary": {
                "total": len(findings),
                "by_severity": _count_by(findings, "severity"),
                "by_category": _count_by(findings, "category"),
                "by_type": _count_by(findings, "finding_type"),
            },
            "inventory_summary": {
                "total_resources": len(resources),
                "by_provider": _count_by(resources, "provider"),
                "by_category": _count_by(resources, "resource_type"),
                "public_resources": sum(1 for resource in resources if resource.exposure_level == "public"),
                "untagged_resources": sum(
                    1 for resource in resources if not resource.owner or not resource.cost_center or not resource.application
                ),
            },
            "top_findings": [self._finding_summary(finding) for finding in top_findings],
            "findings_detail": [self._finding_detail(finding) for finding in detailed_findings],
            "resource_samples": [self._resource_summary(resource) for resource in resources[:50]],
            "ai": self._ai_summary(ai_analysis),
            "limitations": self._limitations(resources=resources, findings=findings, scores=score_map, ai_analysis=ai_analysis),
        }

    def _resources(self, tenant_id: uuid.UUID, *, provider: str | None, cloud_account_id: uuid.UUID | None) -> list[Resource]:
        statement = select(Resource).where(Resource.tenant_id == tenant_id).order_by(Resource.discovered_at.desc())
        if provider:
            statement = statement.where(Resource.provider == provider)
        if cloud_account_id:
            statement = statement.where(Resource.cloud_account_id == cloud_account_id)
        return list(self.db.scalars(statement))

    def _findings(self, tenant_id: uuid.UUID, *, provider: str | None, cloud_account_id: uuid.UUID | None) -> list[Finding]:
        statement = select(Finding).where(Finding.tenant_id == tenant_id).order_by(Finding.last_seen_at.desc())
        if provider:
            statement = statement.where(Finding.provider == provider)
        if cloud_account_id:
            statement = statement.where(Finding.cloud_account_id == cloud_account_id)
        return list(self.db.scalars(statement))

    def _scores(self, tenant_id: uuid.UUID, *, provider: str | None, cloud_account_id: uuid.UUID | None) -> list[CloudScore]:
        statement = select(CloudScore).where(CloudScore.tenant_id == tenant_id).order_by(CloudScore.calculated_at.desc())
        if provider:
            statement = statement.where(CloudScore.provider == provider)
        if cloud_account_id:
            statement = statement.where(CloudScore.cloud_account_id == cloud_account_id)
        return list(self.db.scalars(statement))

    def _latest_ai_analysis(
        self,
        tenant_id: uuid.UUID,
        *,
        report_type: ReportType,
        provider: str | None,
        cloud_account_id: uuid.UUID | None,
    ) -> AIAnalysis | None:
        statement = select(AIAnalysis).where(AIAnalysis.tenant_id == tenant_id, AIAnalysis.status == "completed")
        if provider:
            statement = statement.where(AIAnalysis.provider == provider)
        if cloud_account_id:
            statement = statement.where(AIAnalysis.cloud_account_id == cloud_account_id)
        if report_type == ReportType.EXECUTIVE:
            statement = statement.where(AIAnalysis.analysis_type.in_(["executive_summary", "full_assessment"]))
        else:
            statement = statement.where(AIAnalysis.analysis_type.in_(["technical_assessment", "full_assessment"]))
        return self.db.scalar(statement.order_by(AIAnalysis.created_at.desc()))

    def _finding_summary(self, finding: Finding) -> dict[str, Any]:
        return {
            "title": finding.title,
            "severity": finding.severity,
            "category": finding.category,
            "provider": finding.provider,
            "finding_type": finding.finding_type,
            "recommendation": finding.recommendation,
        }

    def _finding_detail(self, finding: Finding) -> dict[str, Any]:
        data = self._finding_summary(finding)
        data.update(
            {
                "description": finding.description,
                "status": finding.status,
                "evidence": sanitize_value(finding.evidence),
                "resource_id": str(finding.resource_id) if finding.resource_id else None,
            }
        )
        return data

    def _resource_summary(self, resource: Resource) -> dict[str, Any]:
        return {
            "provider": resource.provider,
            "category": resource.resource_type,
            "name": resource.name or resource.resource_id,
            "region": resource.region,
            "status": resource.lifecycle_status or resource.status,
            "exposure": resource.exposure_level,
            "environment": resource.environment,
            "owner_present": bool(resource.owner),
        }

    def _ai_summary(self, analysis: AIAnalysis | None) -> dict[str, Any]:
        if analysis is None:
            return {"available": False, "limitations": ["No completed AI analysis was available for this scope."]}
        return {
            "available": True,
            "analysis_id": str(analysis.id),
            "analysis_type": analysis.analysis_type,
            "provider": analysis.ai_provider,
            "output": sanitize_value(analysis.output),
        }

    def _limitations(
        self,
        *,
        resources: list[Resource],
        findings: list[Finding],
        scores: dict[str, int],
        ai_analysis: AIAnalysis | None,
    ) -> list[str]:
        limitations: list[str] = []
        if not resources:
            limitations.append("No resources were available for this report scope.")
        if not findings:
            limitations.append("No findings were available for this report scope.")
        if not scores:
            limitations.append("No scores were available for this report scope.")
        if ai_analysis is None:
            limitations.append("No completed AI analysis was available; AI narrative sections are limited.")
        return limitations
