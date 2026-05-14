from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from core.database import get_db
from models.cloud_account import CloudAccount
from models.cloud_score import CloudScore
from models.finding import Finding
from models.resource import Resource
from models.tenant import Tenant
from models.user import User

router = APIRouter()


def _assert_tenant_access(current_user: User, tenant_id: uuid.UUID | None) -> uuid.UUID:
    if tenant_id is None:
        return current_user.tenant_id
    if current_user.role != "ADMIN" and tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant access denied")
    return tenant_id


def _score_label(value: int) -> str:
    if value >= 90:
        return "Excellent"
    if value >= 75:
        return "Good"
    if value >= 60:
        return "Fair"
    if value >= 40:
        return "Poor"
    return "Critical"


def _dimension(score: CloudScore | None, key: str, label: str) -> dict[str, object]:
    value = max(0, min(100, int(score.score_value if score else 100)))
    return {
        "key": key,
        "label": label,
        "score": value,
        "label_text": _score_label(value),
        "trend": score.trend if score else "unknown",
        "top_driver": score.summary if score else None,
    }


@router.get("/executive")
def get_executive_dashboard(
    tenant_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    scoped_tenant_id = _assert_tenant_access(current_user, tenant_id)
    tenant = db.get(Tenant, scoped_tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    accounts = db.scalars(select(CloudAccount).where(CloudAccount.tenant_id == scoped_tenant_id)).all()
    resources = db.scalars(select(Resource).where(Resource.tenant_id == scoped_tenant_id)).all()
    findings = db.scalars(
        select(Finding).where(Finding.tenant_id == scoped_tenant_id, Finding.status.in_(["open", "acknowledged"]))
    ).all()
    latest_scores = db.scalars(
        select(CloudScore)
        .where(CloudScore.tenant_id == scoped_tenant_id)
        .order_by(CloudScore.score_type, CloudScore.calculated_at.desc())
    ).all()
    scores_by_type: dict[str, CloudScore] = {}
    for score in latest_scores:
        scores_by_type.setdefault(score.score_type, score)

    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    risk_counts: dict[str, dict[str, object]] = {}
    for finding in findings:
        severity = "low" if finding.severity == "informational" else finding.severity
        if severity in severity_counts:
            severity_counts[severity] += 1
        item = risk_counts.setdefault(
            finding.finding_type,
            {"type": finding.finding_type, "label": finding.finding_type.replace("_", " ").title(), "count": 0, "severity": severity},
        )
        item["count"] = int(item["count"]) + 1
        if ["low", "medium", "high", "critical"].index(severity) > ["low", "medium", "high", "critical"].index(str(item["severity"])):
            item["severity"] = severity

    timestamps = [
        *(resource.discovered_at for resource in resources),
        *(score.calculated_at for score in scores_by_type.values()),
    ]
    latest = max(timestamps) if timestamps else datetime.now(UTC)

    score_specs = [
        ("finops", "FinOps"),
        ("governance", "Governance"),
        ("observability", "Observability"),
        ("security_baseline", "Security"),
        ("resilience", "Resilience"),
    ]

    return {
        "tenant": {"id": str(tenant.id), "name": tenant.name, "slug": tenant.slug, "industry": tenant.industry},
        "cloud_accounts": [
            {
                "id": str(account.id),
                "name": account.name,
                "provider": account.provider,
                "account_id": account.account_id,
                "default_region": account.default_region,
            }
            for account in accounts
        ],
        "overall_score": _dimension(scores_by_type.get("overall"), "overall", "Overall Score"),
        "dimension_scores": [_dimension(scores_by_type.get(key), key, label) for key, label in score_specs],
        "findings": {
            **severity_counts,
            "open": len(findings),
            "cloud_accounts": len(accounts),
            "providers": sorted({account.provider.upper() for account in accounts} | {resource.provider.upper() for resource in resources}),
        },
        "inventory": {
            "total_resources": len(resources),
            "public_resources": sum(1 for resource in resources if resource.exposure_level == "public"),
            "untagged_resources": sum(
                1
                for resource in resources
                if resource.environment in (None, "unknown") or not resource.owner or not resource.cost_center or not resource.application
            ),
        },
        "risks": sorted(risk_counts.values(), key=lambda item: int(item["count"]), reverse=True)[:6],
        "last_collected_at": latest.isoformat(),
        "account_names": [account.name for account in accounts],
    }
