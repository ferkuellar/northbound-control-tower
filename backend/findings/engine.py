from __future__ import annotations

import hashlib
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from findings.enums import FindingSeverity, FindingStatus
from findings.registry import FindingRuleRegistry
from findings.rules import BaseFindingRule
from models.finding import Finding
from models.resource import Resource

logger = logging.getLogger(__name__)


@dataclass
class FindingsRunSummary:
    scan_id: uuid.UUID | None
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID | None
    provider: str | None
    resources_evaluated: int = 0
    findings_created: int = 0
    findings_updated: int = 0
    findings_by_type: dict[str, int] = field(default_factory=dict)
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    rule_errors: int = 0
    execution_time_ms: int = 0


class FindingsEngine:
    def __init__(self, db: Session, registry: FindingRuleRegistry | None = None) -> None:
        self.db = db
        self.registry = registry or FindingRuleRegistry()

    def run(
        self,
        *,
        tenant_id: uuid.UUID,
        cloud_account_id: uuid.UUID | None = None,
        provider: str | None = None,
        scan_id: uuid.UUID | None = None,
    ) -> FindingsRunSummary:
        started = time.perf_counter()
        resources = self._load_resources(tenant_id=tenant_id, cloud_account_id=cloud_account_id, provider=provider)
        summary = FindingsRunSummary(
            scan_id=scan_id,
            tenant_id=tenant_id,
            cloud_account_id=cloud_account_id,
            provider=provider,
            resources_evaluated=len(resources),
        )
        for resource in resources:
            for rule in self.registry.rules():
                self._evaluate_rule(rule, resource, summary)
        self.db.flush()
        summary.execution_time_ms = int((time.perf_counter() - started) * 1000)
        return summary

    def fingerprint(self, resource: Resource, rule: BaseFindingRule) -> str:
        parts = [
            str(resource.tenant_id),
            str(resource.cloud_account_id),
            resource.provider,
            str(resource.id),
            rule.finding_type.value,
            rule.rule_id,
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def _load_resources(
        self,
        *,
        tenant_id: uuid.UUID,
        cloud_account_id: uuid.UUID | None,
        provider: str | None,
    ) -> list[Resource]:
        statement = select(Resource).where(Resource.tenant_id == tenant_id)
        if cloud_account_id:
            statement = statement.where(Resource.cloud_account_id == cloud_account_id)
        if provider:
            statement = statement.where(Resource.provider == provider)
        return list(self.db.scalars(statement))

    def _evaluate_rule(self, rule: BaseFindingRule, resource: Resource, summary: FindingsRunSummary) -> None:
        try:
            candidate = rule.evaluate(resource)
            if candidate is None:
                return
            severity = candidate.evidence.get("severity_hint", rule.severity.value)
            severity = severity if severity in {item.value for item in FindingSeverity} else rule.severity.value
            finding = self._upsert_finding(
                resource=resource,
                rule=rule,
                severity=severity,
                candidate={
                    "title": candidate.title,
                    "description": candidate.description,
                    "evidence": self._safe_evidence(candidate.evidence),
                    "recommendation": candidate.recommendation,
                    "estimated_monthly_waste": candidate.estimated_monthly_waste,
                },
            )
            if finding.created_at is None:
                summary.findings_created += 1
            else:
                summary.findings_updated += 1
            summary.findings_by_type[rule.finding_type.value] = summary.findings_by_type.get(rule.finding_type.value, 0) + 1
            summary.findings_by_severity[severity] = summary.findings_by_severity.get(severity, 0) + 1
        except Exception:
            summary.rule_errors += 1
            logger.exception(
                "Finding rule evaluation failed",
                extra={
                    "rule_id": rule.rule_id,
                    "provider": resource.provider,
                    "resource_id": resource.resource_id,
                    "resource_pk": str(resource.id),
                    "cloud_account_id": str(resource.cloud_account_id),
                    "tenant_id": str(resource.tenant_id),
                },
            )

    def _upsert_finding(
        self,
        *,
        resource: Resource,
        rule: BaseFindingRule,
        severity: str,
        candidate: dict[str, Any],
    ) -> Finding:
        now = datetime.now(UTC)
        fingerprint = self.fingerprint(resource, rule)
        finding = self.db.scalar(select(Finding).where(Finding.fingerprint == fingerprint))
        if finding is None:
            finding = Finding(
                tenant_id=resource.tenant_id,
                cloud_account_id=resource.cloud_account_id,
                resource_id=resource.id,
                provider=resource.provider,
                finding_type=rule.finding_type.value,
                category=rule.category.value,
                severity=severity,
                status=FindingStatus.OPEN.value,
                rule_id=rule.rule_id,
                fingerprint=fingerprint,
                first_seen_at=now,
            )
            self.db.add(finding)
        finding.title = candidate["title"]
        finding.description = candidate["description"]
        finding.evidence = candidate["evidence"]
        finding.recommendation = candidate["recommendation"]
        finding.estimated_monthly_waste = candidate["estimated_monthly_waste"]
        finding.severity = severity
        finding.last_seen_at = now
        return finding

    def _safe_evidence(self, evidence: dict[str, Any]) -> dict[str, Any]:
        blocked = {"secret", "secret_access_key", "private_key", "private_key_passphrase", "token", "password", "key_content"}
        return {key: value for key, value in evidence.items() if key.lower() not in blocked}
