from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningApproval, ProvisioningRequest
from provisioning.approval_snapshots import artifact_by_type
from provisioning.artifact_service import ProvisioningArtifactService
from provisioning.checksum_service import ChecksumService
from provisioning.enums import ProvisioningApprovalDecision, ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.workspace_security import resolve_request_workspace


@dataclass(frozen=True)
class ApplyPrecheckResult:
    passed: bool
    request: ProvisioningRequest | None
    workspace_path: Path | None
    approval: ProvisioningApproval | None
    checks: list[dict[str, str]] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)

    def payload(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "request_id": self.request.request_number if self.request else None,
            "reasons": self.reasons,
            "checks": self.checks,
            "generated_at": datetime.now(UTC).isoformat(),
        }


class ApplyPrecheckService:
    def __init__(
        self,
        db: Session,
        *,
        artifact_service: ProvisioningArtifactService | None = None,
        checksum_service: ChecksumService | None = None,
    ) -> None:
        self.db = db
        self.artifact_service = artifact_service or ProvisioningArtifactService(db)
        self.checksum_service = checksum_service or ChecksumService()

    def run(self, request: ProvisioningRequest | None, *, created_by_user_id: str | None = None) -> ApplyPrecheckResult:
        checks: list[dict[str, str]] = []
        reasons: list[str] = []
        workspace_path: Path | None = None
        approval: ProvisioningApproval | None = None

        if request is None:
            return ApplyPrecheckResult(False, None, None, None, reasons=["Provisioning request does not exist"])

        original_status = request.status
        request.status = ProvisioningRequestStatus.APPLY_PRECHECK_RUNNING.value
        self.db.flush()

        approval = self._approval(request)
        self._check(checks, reasons, "request_status", original_status == ProvisioningRequestStatus.APPROVED.value, f"Request status must be APPROVED, current status is {original_status}")
        if request.status == ProvisioningRequestStatus.APPLY_PRECHECK_RUNNING.value and (request.evidence or {}).get("approval"):
            self._pass(checks, "approval_evidence", "Approval evidence exists")
        if approval is None:
            self._fail(checks, reasons, "approval_record", "Approved approval record not found")
        else:
            self._check(checks, reasons, "approval_decision", approval.decision == ProvisioningApprovalDecision.APPROVED.value, "Approval decision is APPROVED")
            expired = approval.expires_at is not None and approval.expires_at <= datetime.now(UTC)
            self._check(checks, reasons, "approval_not_expired", not expired, "Approval is not expired")

        try:
            workspace_path = resolve_request_workspace(request)
            self._pass(checks, "workspace", "Workspace path is valid")
        except ValueError as exc:
            self._fail(checks, reasons, "workspace", str(exc))

        plan_artifact = artifact_by_type(self.db, request, ProvisioningArtifactType.TERRAFORM_PLAN_BINARY)
        plan_json_artifact = artifact_by_type(self.db, request, ProvisioningArtifactType.TERRAFORM_PLAN_JSON)
        risk_artifact = artifact_by_type(self.db, request, ProvisioningArtifactType.RISK_SUMMARY_JSON)
        gates_artifact = artifact_by_type(self.db, request, ProvisioningArtifactType.GATES_RESULT_JSON)
        for name, artifact in (
            ("plan.out", plan_artifact),
            ("plan.json", plan_json_artifact),
            ("risk-summary.json", risk_artifact),
            ("gates-result.json", gates_artifact),
        ):
            self._check(checks, reasons, f"{name}_artifact", artifact is not None, f"{name} artifact exists")

        if workspace_path:
            self._verify_checksum(checks, reasons, workspace_path / "plan.out", workspace_path, approval.approved_plan_checksum_sha256 if approval else None, "plan_checksum")
            self._verify_checksum(checks, reasons, workspace_path / "plan.json", workspace_path, approval.approved_plan_json_checksum_sha256 if approval else None, "plan_json_checksum")
            self._verify_checksum(checks, reasons, workspace_path / "risk-summary.json", workspace_path, approval.approved_risk_summary_checksum_sha256 if approval else None, "risk_summary_checksum")
            self._verify_checksum(checks, reasons, workspace_path / "gates-result.json", workspace_path, approval.approved_gates_result_checksum_sha256 if approval else None, "gates_result_checksum")

        gates = approval.gates_snapshot_json if approval else (request.evidence or {}).get("policy_gates") or {}
        plan = approval.plan_summary_snapshot_json if approval else (request.evidence or {}).get("terraform_plan") or {}
        self._check(checks, reasons, "gates_not_blocked", gates.get("blocked") is not True and gates.get("decision") != ProvisioningRequestStatus.GATES_BLOCKED.value, "Gates are not blocked")
        destructive = plan.get("has_destructive_changes") is True or int(plan.get("delete_count") or 0) > 0 or int(plan.get("replace_count") or 0) > 0
        self._check(checks, reasons, "no_destructive_changes", not destructive, "No destructive changes detected")

        passed = not reasons
        request.status = ProvisioningRequestStatus.APPLY_READY.value if passed else ProvisioningRequestStatus.APPLY_PRECHECK_FAILED.value
        result = ApplyPrecheckResult(passed, request, workspace_path, approval, checks=checks, reasons=reasons)
        if workspace_path:
            self.artifact_service.create_json_file(
                request=request,
                artifact_type=ProvisioningArtifactType.TERRAFORM_APPLY_PRECHECK_RESULT,
                path=workspace_path / "apply-precheck-result.json",
                workspace_root=workspace_path,
                payload=result.payload(),
                created_by_user_id=created_by_user_id,
            )
        request.evidence = {**(request.evidence or {}), "apply_precheck": result.payload()}
        self.db.flush()
        return result

    def _approval(self, request: ProvisioningRequest) -> ProvisioningApproval | None:
        return self.db.scalar(
            select(ProvisioningApproval)
            .where(ProvisioningApproval.request_id == request.id)
            .where(ProvisioningApproval.decision == ProvisioningApprovalDecision.APPROVED.value)
            .order_by(ProvisioningApproval.decided_at.desc())
        )

    def _verify_checksum(self, checks: list[dict[str, str]], reasons: list[str], path: Path, workspace_path: Path, approved: str | None, name: str) -> None:
        if not approved:
            self._fail(checks, reasons, name, "Approved checksum is missing")
            return
        try:
            current = self.checksum_service.sha256_file(path, workspace_root=workspace_path)
        except (FileNotFoundError, ValueError) as exc:
            self._fail(checks, reasons, name, str(exc))
            return
        self._check(checks, reasons, name, current == approved, f"{name} verified")

    def _check(self, checks: list[dict[str, str]], reasons: list[str], name: str, condition: bool, message: str) -> None:
        if condition:
            self._pass(checks, name, message)
        else:
            self._fail(checks, reasons, name, message)

    def _pass(self, checks: list[dict[str, str]], name: str, message: str) -> None:
        checks.append({"name": name, "result": "PASS", "message": message})

    def _fail(self, checks: list[dict[str, str]], reasons: list[str], name: str, message: str) -> None:
        checks.append({"name": name, "result": "FAIL", "message": message})
        reasons.append(message)
