from __future__ import annotations

import uuid
from collections import Counter
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.config import settings
from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant

SECRET_KEYWORDS = ("secret", "password", "private_key", "passphrase", "token", "api_key", "access_key", "fingerprint")


def _safe_dict(value: dict[str, Any] | None) -> dict[str, Any]:
    if not value:
        return {}
    sanitized: dict[str, Any] = {}
    for key, item in value.items():
        lowered = key.lower()
        if any(secret in lowered for secret in SECRET_KEYWORDS):
            continue
        if isinstance(item, dict):
            sanitized[key] = _safe_dict(item)
        elif isinstance(item, list):
            sanitized[key] = [_safe_dict(entry) if isinstance(entry, dict) else entry for entry in item[:20]]
        elif isinstance(item, str) and any(marker in item for marker in ("-----BEGIN", "AKIA", "Bearer ")):
            continue
        else:
            sanitized[key] = item
    return sanitized


def _count_by(items: list[Any], attr: str) -> dict[str, int]:
    counter = Counter(str(getattr(item, attr) or "unknown") for item in items)
    return dict(counter)


class AIContextBuilder:
    def __init__(self, db: Session) -> None:
        self.db = db

    def build(
        self,
        *,
        tenant_id: uuid.UUID,
        cloud_account_id: uuid.UUID | None = None,
        cloud_provider: str | None = None,
    ) -> dict[str, Any]:
        tenant = self.db.get(Tenant, tenant_id)
        account_statement = select(CloudAccount).where(CloudAccount.tenant_id == tenant_id)
        if cloud_account_id:
            account_statement = account_statement.where(CloudAccount.id == cloud_account_id)
        if cloud_provider:
            account_statement = account_statement.where(CloudAccount.provider == cloud_provider)
        cloud_accounts = list(self.db.scalars(account_statement))

        score_statement = select(CloudScore).where(CloudScore.tenant_id == tenant_id).order_by(CloudScore.calculated_at.desc())
        if cloud_account_id:
            score_statement = score_statement.where(CloudScore.cloud_account_id == cloud_account_id)
        if cloud_provider:
            score_statement = score_statement.where(CloudScore.provider == cloud_provider)
        scores = list(self.db.scalars(score_statement))
        latest_scores: dict[str, int] = {}
        for score in scores:
            latest_scores.setdefault(score.score_type, score.score_value)

        finding_statement = select(Finding).where(
            Finding.tenant_id == tenant_id,
            Finding.status.in_(["open", "acknowledged"]),
        )
        if cloud_account_id:
            finding_statement = finding_statement.where(Finding.cloud_account_id == cloud_account_id)
        if cloud_provider:
            finding_statement = finding_statement.where(Finding.provider == cloud_provider)
        findings = list(self.db.scalars(finding_statement.order_by(Finding.last_seen_at.desc())))

        resource_statement = select(Resource).where(Resource.tenant_id == tenant_id)
        if cloud_account_id:
            resource_statement = resource_statement.where(Resource.cloud_account_id == cloud_account_id)
        if cloud_provider:
            resource_statement = resource_statement.where(Resource.provider == cloud_provider)
        resources = list(self.db.scalars(resource_statement.order_by(Resource.discovered_at.desc())))

        top_findings = [
            {
                "id": str(finding.id),
                "provider": finding.provider,
                "finding_type": finding.finding_type,
                "category": finding.category,
                "severity": finding.severity,
                "title": finding.title,
                "recommendation": finding.recommendation,
                "evidence": _safe_dict(finding.evidence),
            }
            for finding in findings[: settings.ai_max_input_findings]
        ]
        resource_samples = [
            {
                "id": str(resource.id),
                "provider": resource.provider,
                "resource_category": resource.resource_type,
                "name": resource.name or resource.resource_id,
                "region": resource.region,
                "lifecycle_status": resource.lifecycle_status,
                "exposure_level": resource.exposure_level,
                "environment": resource.environment,
                "criticality": resource.criticality,
                "owner_present": bool(resource.owner),
                "cost_center_present": bool(resource.cost_center),
                "application_present": bool(resource.application),
                "metadata": _safe_dict(
                    {
                        "service_name": resource.service_name,
                        "raw_type": resource.raw_type,
                        "status": resource.status,
                    }
                ),
            }
            for resource in resources[: settings.ai_max_input_resources]
        ]

        return {
            "tenant": {"id": str(tenant_id), "name": tenant.name if tenant else "unknown"},
            "scope": {
                "provider": cloud_provider or "all",
                "cloud_account_id": str(cloud_account_id) if cloud_account_id else None,
            },
            "scores": latest_scores,
            "findings_summary": {
                "total_open": len(findings),
                "critical": sum(1 for finding in findings if finding.severity == "critical"),
                "high": sum(1 for finding in findings if finding.severity == "high"),
                "medium": sum(1 for finding in findings if finding.severity == "medium"),
                "low": sum(1 for finding in findings if finding.severity == "low"),
                "by_type": _count_by(findings, "finding_type"),
                "by_category": _count_by(findings, "category"),
                "top_findings": top_findings,
            },
            "inventory_summary": {
                "total_resources": len(resources),
                "by_provider": _count_by(resources, "provider"),
                "by_category": _count_by(resources, "resource_type"),
                "public_resources": sum(1 for resource in resources if resource.exposure_level == "public"),
                "untagged_resources": sum(
                    1 for resource in resources if not resource.owner or not resource.cost_center or not resource.application
                ),
                "resource_samples": resource_samples,
            },
            "cloud_accounts": [
                {
                    "id": str(account.id),
                    "provider": account.provider,
                    "name": account.name,
                    "region": account.region or account.default_region,
                    "is_active": account.is_active,
                }
                for account in cloud_accounts
            ],
            "limitations": {
                "scores_available": bool(latest_scores),
                "findings_available": bool(findings),
                "resources_available": bool(resources),
                "resource_sample_limit": settings.ai_max_input_resources,
                "finding_limit": settings.ai_max_input_findings,
            },
        }
