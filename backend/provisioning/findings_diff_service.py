from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from models.finding import Finding

SEVERITY_ORDER = {
    "informational": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


@dataclass(frozen=True)
class FindingsDiff:
    outcome: str
    payload: dict[str, Any]
    checks: list[dict[str, str]]


def finding_snapshot(finding: Finding | None) -> dict[str, Any]:
    if finding is None:
        return {"status": "NOT_FOUND"}
    return {
        "id": str(finding.id),
        "cloud_account_id": str(finding.cloud_account_id),
        "resource_id": str(finding.resource_id) if finding.resource_id else None,
        "provider": finding.provider,
        "finding_type": finding.finding_type,
        "category": finding.category,
        "severity": finding.severity,
        "status": finding.status,
        "title": finding.title,
        "rule_id": finding.rule_id,
        "fingerprint": finding.fingerprint,
        "last_seen_at": finding.last_seen_at.isoformat() if finding.last_seen_at else None,
        "evidence": finding.evidence or {},
    }


class FindingsDiffService:
    def build_diff(
        self,
        *,
        before: Finding | None,
        after: Finding | None,
        validation_started_at: datetime,
        collector_succeeded: bool,
        findings_engine_succeeded: bool,
    ) -> FindingsDiff:
        before_snapshot = finding_snapshot(before)
        after_snapshot = finding_snapshot(after)
        checks = [
            self._check("collector_completed", collector_succeeded, "Collector completed successfully", "Collector failed"),
            self._check("findings_engine_completed", findings_engine_succeeded, "Findings engine completed successfully", "Findings engine failed"),
        ]
        if not collector_succeeded or not findings_engine_succeeded or before is None:
            checks.append({"name": "sufficient_data", "status": "FAIL", "message": "Validation data is incomplete"})
            outcome = "VALIDATION_FAILED"
            return FindingsDiff(outcome, self._payload(before_snapshot, after_snapshot, outcome), checks)

        active_after = self._active_in_current_run(after, validation_started_at)
        checks.append(self._check("original_finding_absent", not active_after, "Original finding is no longer active", "Original finding remains active"))
        checks.append(self._check("equivalent_finding_absent", not active_after, "No equivalent finding exists for same resource/rule", "Equivalent finding remains active"))

        if after is None or not active_after:
            outcome = "RESOLVED"
        elif self._severity_improved(before.severity, after.severity):
            outcome = "PARTIALLY_RESOLVED"
        else:
            outcome = "STILL_OPEN"
        return FindingsDiff(outcome, self._payload(before_snapshot, after_snapshot, outcome), checks)

    def _active_in_current_run(self, finding: Finding | None, validation_started_at: datetime) -> bool:
        if finding is None:
            return False
        if finding.status not in {"open", "acknowledged", "remediation_running", "validating", "still_open"}:
            return False
        return finding.last_seen_at is not None and finding.last_seen_at >= validation_started_at

    def _severity_improved(self, before: str, after: str) -> bool:
        return SEVERITY_ORDER.get(after, 99) < SEVERITY_ORDER.get(before, 99)

    def _payload(self, before: dict[str, Any], after: dict[str, Any], outcome: str) -> dict[str, Any]:
        return {
            "finding_id": before.get("id"),
            "resource_id": before.get("resource_id"),
            "rule_id": before.get("rule_id"),
            "before": before,
            "after": after,
            "outcome": outcome,
        }

    def _check(self, name: str, passed: bool, pass_message: str, fail_message: str) -> dict[str, str]:
        return {"name": name, "status": "PASS" if passed else "FAIL", "message": pass_message if passed else fail_message}
