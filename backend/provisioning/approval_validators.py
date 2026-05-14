from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from cloud_shell.authorization import ROLE_RANK
from cloud_shell.schemas import ShellUserContext
from models.provisioning_request import ProvisioningRequest
from provisioning.approval_snapshots import artifact_by_type, approval_snapshots
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus


APPROVAL_ROLES = {"APPROVER", "ADMIN", "BREAKGLASS_ADMIN"}
APPROVABLE_STATUSES = {ProvisioningRequestStatus.READY_FOR_APPROVAL.value, ProvisioningRequestStatus.PENDING_APPROVAL.value}
INVALID_APPROVAL_STATUSES = {
    ProvisioningRequestStatus.GATES_BLOCKED.value,
    ProvisioningRequestStatus.CANCELLED.value,
    ProvisioningRequestStatus.REJECTED.value,
    ProvisioningRequestStatus.APPROVED.value,
    ProvisioningRequestStatus.PLAN_FAILED.value,
    ProvisioningRequestStatus.SECURITY_SCAN_BLOCKED.value,
    ProvisioningRequestStatus.VALIDATION_FAILED.value,
}
TERMINAL_STATUSES = {
    ProvisioningRequestStatus.APPROVED.value,
    ProvisioningRequestStatus.REJECTED.value,
    ProvisioningRequestStatus.CANCELLED.value,
    ProvisioningRequestStatus.APPROVAL_EXPIRED.value,
}


@dataclass(frozen=True)
class ApprovalValidationResult:
    allowed: bool
    reasons: list[str]


def user_can_approve(user_context: ShellUserContext) -> bool:
    return user_context.role in APPROVAL_ROLES or ROLE_RANK.get(user_context.role, 0) >= ROLE_RANK["APPROVER"]


class ApprovalValidator:
    def __init__(self, db: Session) -> None:
        self.db = db

    def validate_approve(self, request: ProvisioningRequest | None, user_context: ShellUserContext) -> ApprovalValidationResult:
        reasons: list[str] = []
        if request is None:
            return ApprovalValidationResult(False, ["Provisioning request does not exist"])
        if not user_can_approve(user_context):
            reasons.append("User must have APPROVER or ADMIN role")
        if request.status in INVALID_APPROVAL_STATUSES:
            reasons.append(f"Request status {request.status} cannot be approved")
        if request.status not in APPROVABLE_STATUSES:
            reasons.append(f"Request must be READY_FOR_APPROVAL or PENDING_APPROVAL, not {request.status}")
        if not artifact_by_type(self.db, request, ProvisioningArtifactType.TERRAFORM_PLAN_JSON):
            reasons.append("Terraform plan artifact is missing")
        if not artifact_by_type(self.db, request, ProvisioningArtifactType.RISK_SUMMARY_JSON):
            reasons.append("Risk summary artifact is missing")
        if not artifact_by_type(self.db, request, ProvisioningArtifactType.GATES_RESULT_JSON):
            reasons.append("Gates result artifact is missing")

        snapshots = approval_snapshots(self.db, request)
        gates = snapshots["gates"]
        plan = snapshots["plan_summary"]
        security = snapshots["security"]
        if gates.get("blocked") is True or gates.get("decision") == ProvisioningRequestStatus.GATES_BLOCKED.value:
            reasons.append("Policy gates are blocked")
        if plan.get("has_destructive_changes") is True or int(plan.get("delete_count") or 0) > 0 or int(plan.get("replace_count") or 0) > 0:
            reasons.append("Terraform plan includes destructive changes")
        if security.get("highest_severity") == "CRITICAL":
            reasons.append("Critical security finding is present")
        return ApprovalValidationResult(not reasons, reasons)

    def validate_reject(self, request: ProvisioningRequest | None, note: str, user_context: ShellUserContext) -> ApprovalValidationResult:
        reasons: list[str] = []
        if request is None:
            return ApprovalValidationResult(False, ["Provisioning request does not exist"])
        if not user_can_approve(user_context):
            reasons.append("User must have APPROVER or ADMIN role")
        if request.status in TERMINAL_STATUSES:
            reasons.append(f"Request status {request.status} is terminal")
        if not note.strip():
            reasons.append("Rejection note is required")
        return ApprovalValidationResult(not reasons, reasons)
