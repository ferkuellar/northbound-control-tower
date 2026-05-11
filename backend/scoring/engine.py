from __future__ import annotations

import time
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from findings.enums import FindingStatus
from models.cloud_score import CloudScore
from models.finding import Finding
from models.resource import Resource
from scoring.enums import ScoreType
from scoring.formulas import calculate_score, calculate_weighted_overall, grade_for_score, trend_for_scores
from scoring.weights import (
    FORMULA_VERSION,
    OVERALL_WEIGHTS,
    SCORE_TYPE_DEDUCTION_MULTIPLIERS,
    SCORE_TYPE_FINDING_MAP,
    SEVERITY_DEDUCTIONS,
)


@dataclass
class ScoreRunResult:
    tenant_id: uuid.UUID
    cloud_account_id: uuid.UUID | None
    provider: str | None
    scores: list[CloudScore]
    execution_time_ms: int


class RiskScoringEngine:
    def __init__(self, db: Session) -> None:
        self.db = db

    def calculate(
        self,
        *,
        tenant_id: uuid.UUID,
        cloud_account_id: uuid.UUID | None = None,
        provider: str | None = None,
    ) -> ScoreRunResult:
        started = time.perf_counter()
        findings = self._load_findings(tenant_id=tenant_id, cloud_account_id=cloud_account_id, provider=provider)
        total_resources = self._count_resources(tenant_id=tenant_id, cloud_account_id=cloud_account_id, provider=provider)
        scores: list[CloudScore] = []
        domain_values: dict[str, int] = {}

        for score_type in [
            ScoreType.FINOPS,
            ScoreType.GOVERNANCE,
            ScoreType.OBSERVABILITY,
            ScoreType.SECURITY_BASELINE,
            ScoreType.RESILIENCE,
        ]:
            relevant = self._findings_for_score(findings, score_type)
            multiplier = SCORE_TYPE_DEDUCTION_MULTIPLIERS.get(score_type.value, 1.0)
            score_value = calculate_score(relevant, multiplier=multiplier)
            domain_values[score_type.value] = score_value
            scores.append(
                self._persist_score(
                    tenant_id=tenant_id,
                    cloud_account_id=cloud_account_id,
                    provider=provider,
                    score_type=score_type,
                    score_value=score_value,
                    findings=relevant,
                    all_findings=findings,
                    total_resources=total_resources,
                    weights_used={"severity_deductions": SEVERITY_DEDUCTIONS, "multiplier": multiplier},
                )
            )

        overall_value = calculate_weighted_overall(domain_values)
        scores.append(
            self._persist_score(
                tenant_id=tenant_id,
                cloud_account_id=cloud_account_id,
                provider=provider,
                score_type=ScoreType.OVERALL,
                score_value=overall_value,
                findings=findings,
                all_findings=findings,
                total_resources=total_resources,
                weights_used={"overall_weights": OVERALL_WEIGHTS},
                domain_scores=domain_values,
            )
        )
        self.db.flush()
        return ScoreRunResult(
            tenant_id=tenant_id,
            cloud_account_id=cloud_account_id,
            provider=provider,
            scores=scores,
            execution_time_ms=int((time.perf_counter() - started) * 1000),
        )

    def _load_findings(
        self,
        *,
        tenant_id: uuid.UUID,
        cloud_account_id: uuid.UUID | None,
        provider: str | None,
    ) -> list[Finding]:
        statement = select(Finding).where(
            Finding.tenant_id == tenant_id,
            Finding.status.in_([FindingStatus.OPEN.value, FindingStatus.ACKNOWLEDGED.value]),
        )
        if cloud_account_id:
            statement = statement.where(Finding.cloud_account_id == cloud_account_id)
        if provider:
            statement = statement.where(Finding.provider == provider)
        return list(self.db.scalars(statement))

    def _count_resources(self, *, tenant_id: uuid.UUID, cloud_account_id: uuid.UUID | None, provider: str | None) -> int:
        statement = select(Resource).where(Resource.tenant_id == tenant_id)
        if cloud_account_id:
            statement = statement.where(Resource.cloud_account_id == cloud_account_id)
        if provider:
            statement = statement.where(Resource.provider == provider)
        return len(list(self.db.scalars(statement)))

    def _findings_for_score(self, findings: list[Finding], score_type: ScoreType) -> list[Finding]:
        allowed_types = SCORE_TYPE_FINDING_MAP.get(score_type.value, set())
        return [finding for finding in findings if finding.finding_type in allowed_types]

    def _persist_score(
        self,
        *,
        tenant_id: uuid.UUID,
        cloud_account_id: uuid.UUID | None,
        provider: str | None,
        score_type: ScoreType,
        score_value: int,
        findings: list[Finding],
        all_findings: list[Finding],
        total_resources: int,
        weights_used: dict[str, Any],
        domain_scores: dict[str, int] | None = None,
    ) -> CloudScore:
        previous = self._previous_score(
            tenant_id=tenant_id,
            cloud_account_id=cloud_account_id,
            provider=provider,
            score_type=score_type,
        )
        evidence = self._evidence(
            findings=findings,
            all_findings=all_findings,
            total_resources=total_resources,
            provider=provider,
            cloud_account_id=cloud_account_id,
            weights_used=weights_used,
            domain_scores=domain_scores,
        )
        score = CloudScore(
            tenant_id=tenant_id,
            cloud_account_id=cloud_account_id,
            provider=provider,
            score_type=score_type.value,
            score_value=score_value,
            grade=grade_for_score(score_value).value,
            trend=trend_for_scores(score_value, previous.score_value if previous else None).value,
            summary=self._summary(score_type=score_type, score_value=score_value, findings=findings),
            evidence=evidence,
            calculated_at=datetime.now(UTC),
        )
        self.db.add(score)
        return score

    def _previous_score(
        self,
        *,
        tenant_id: uuid.UUID,
        cloud_account_id: uuid.UUID | None,
        provider: str | None,
        score_type: ScoreType,
    ) -> CloudScore | None:
        statement = (
            select(CloudScore)
            .where(
                CloudScore.tenant_id == tenant_id,
                CloudScore.score_type == score_type.value,
                CloudScore.cloud_account_id == cloud_account_id,
                CloudScore.provider == provider,
            )
            .order_by(CloudScore.calculated_at.desc())
        )
        return self.db.scalar(statement)

    def _evidence(
        self,
        *,
        findings: list[Finding],
        all_findings: list[Finding],
        total_resources: int,
        provider: str | None,
        cloud_account_id: uuid.UUID | None,
        weights_used: dict[str, Any],
        domain_scores: dict[str, int] | None,
    ) -> dict[str, Any]:
        findings_by_severity = Counter(finding.severity for finding in all_findings)
        findings_by_type = Counter(finding.finding_type for finding in all_findings)
        deductions = [
            {"finding_id": str(finding.id), "finding_type": finding.finding_type, "severity": finding.severity}
            for finding in findings
        ]
        evidence: dict[str, Any] = {
            "total_resources": total_resources,
            "total_findings": len(all_findings),
            "findings_by_severity": dict(findings_by_severity),
            "findings_by_type": dict(findings_by_type),
            "formula_version": FORMULA_VERSION,
            "weights_used": weights_used,
            "deductions": deductions,
            "provider": provider,
            "cloud_account_id": str(cloud_account_id) if cloud_account_id else None,
            "top_drivers": self._top_drivers(all_findings),
        }
        if domain_scores:
            evidence["domain_scores"] = domain_scores
        return evidence

    def _top_drivers(self, findings: list[Finding]) -> list[dict[str, Any]]:
        by_type = Counter(finding.finding_type for finding in findings)
        critical_high = Counter(
            finding.finding_type for finding in findings if finding.severity in {"critical", "high"}
        )
        return [
            {"finding_type": finding_type, "count": count, "high_or_critical": critical_high.get(finding_type, 0)}
            for finding_type, count in by_type.most_common(5)
        ]

    def _summary(self, *, score_type: ScoreType, score_value: int, findings: list[Finding]) -> str:
        if not findings:
            return f"{score_type.value} score is {score_value}; no active findings affected this score."
        top_type, top_count = Counter(finding.finding_type for finding in findings).most_common(1)[0]
        return f"{score_type.value} score is {score_value}; top driver is {top_type} ({top_count})."
