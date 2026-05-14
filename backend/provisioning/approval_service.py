from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cloud_shell.schemas import ShellUserContext
from models.provisioning_request import ProvisioningApproval, ProvisioningRequest
from provisioning.approval_snapshots import approval_snapshots
from provisioning.approval_validators import ApprovalValidator
from provisioning.enums import ProvisioningApprovalDecision, ProvisioningApprovalLevel, ProvisioningRequestStatus
from provisioning.service import ProvisioningRequestService


@dataclass(frozen=True)
class ApprovalResult:
    approval: ProvisioningApproval
    request: ProvisioningRequest


def _next_approval_code(db: Session) -> str:
    count = db.scalar(select(func.count()).select_from(ProvisioningApproval)) or 0
    return f"APP-{int(count) + 1001}"


class ApprovalService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.validator = ApprovalValidator(db)
        self.requests = ProvisioningRequestService(db)

    def list_pending(self, *, tenant_id: uuid.UUID) -> list[ProvisioningRequest]:
        requests = list(
            self.db.scalars(
                select(ProvisioningRequest)
                .where(ProvisioningRequest.tenant_id == tenant_id)
                .where(ProvisioningRequest.status.in_([ProvisioningRequestStatus.READY_FOR_APPROVAL.value, ProvisioningRequestStatus.PENDING_APPROVAL.value]))
                .order_by(ProvisioningRequest.created_at.asc())
            )
        )
        for request in requests:
            self.ensure_pending_record(request)
        self.db.commit()
        return requests

    def get_detail(self, *, tenant_id: uuid.UUID, identifier: str) -> tuple[ProvisioningRequest | None, ProvisioningApproval | None, dict[str, Any]]:
        request = self.requests.get_by_number_or_id(tenant_id=tenant_id, identifier=identifier)
        if request is None:
            return None, None, {}
        approval = self.ensure_pending_record(request) if request.status in {
            ProvisioningRequestStatus.READY_FOR_APPROVAL.value,
            ProvisioningRequestStatus.PENDING_APPROVAL.value,
        } else self.get_for_request(request)
        snapshots = approval_snapshots(self.db, request)
        self.db.commit()
        return request, approval, snapshots

    def approve(self, *, tenant_id: uuid.UUID, identifier: str, note: str, user_context: ShellUserContext) -> ApprovalResult:
        request = self.requests.get_by_number_or_id(tenant_id=tenant_id, identifier=identifier)
        validation = self.validator.validate_approve(request, user_context)
        if not validation.allowed or request is None:
            raise ValueError("; ".join(validation.reasons))

        approval = self.ensure_pending_record(request)
        snapshots = approval_snapshots(self.db, request)
        approval.approved_by = uuid.UUID(str(user_context.user_id)) if user_context.user_id else None
        approval.decision = ProvisioningApprovalDecision.APPROVED.value
        approval.status = ProvisioningApprovalDecision.APPROVED.value
        approval.approval_note = note.strip()
        approval.rejection_reason = None
        approval.decided_at = datetime.now(UTC)
        self._apply_snapshots(approval, snapshots)
        request.status = ProvisioningRequestStatus.APPROVED.value
        request.evidence = {
            **(request.evidence or {}),
            "approval": {
                "approval_code": approval.approval_code,
                "decision": approval.decision,
                "approved_by": str(approval.approved_by) if approval.approved_by else None,
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
            },
        }
        self.db.commit()
        return ApprovalResult(approval=approval, request=request)

    def reject(self, *, tenant_id: uuid.UUID, identifier: str, note: str, user_context: ShellUserContext) -> ApprovalResult:
        request = self.requests.get_by_number_or_id(tenant_id=tenant_id, identifier=identifier)
        validation = self.validator.validate_reject(request, note, user_context)
        if not validation.allowed or request is None:
            raise ValueError("; ".join(validation.reasons))

        approval = self.ensure_pending_record(request)
        snapshots = approval_snapshots(self.db, request)
        approval.approved_by = uuid.UUID(str(user_context.user_id)) if user_context.user_id else None
        approval.decision = ProvisioningApprovalDecision.REJECTED.value
        approval.status = ProvisioningApprovalDecision.REJECTED.value
        approval.approval_note = None
        approval.rejection_reason = note.strip()
        approval.decided_at = datetime.now(UTC)
        self._apply_snapshots(approval, snapshots)
        request.status = ProvisioningRequestStatus.REJECTED.value
        request.evidence = {
            **(request.evidence or {}),
            "approval": {
                "approval_code": approval.approval_code,
                "decision": approval.decision,
                "rejected_by": str(approval.approved_by) if approval.approved_by else None,
                "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
            },
        }
        self.db.commit()
        return ApprovalResult(approval=approval, request=request)

    def get_for_request(self, request: ProvisioningRequest) -> ProvisioningApproval | None:
        return self.db.scalar(
            select(ProvisioningApproval)
            .where(ProvisioningApproval.request_id == request.id)
            .order_by(ProvisioningApproval.created_at.desc())
        )

    def ensure_pending_record(self, request: ProvisioningRequest) -> ProvisioningApproval:
        approval = self.get_for_request(request)
        if approval is not None:
            return approval

        environment = self._environment(request)
        is_prod = environment.lower() in {"prod", "production"}
        approval = ProvisioningApproval(
            approval_code=_next_approval_code(self.db),
            request_id=request.id,
            tenant_id=request.tenant_id,
            client_id=None,
            cloud_account_id=request.cloud_account_id,
            requested_by=request.requested_by_user_id,
            approved_by=None,
            decision=ProvisioningApprovalDecision.PENDING.value,
            status=ProvisioningApprovalDecision.PENDING.value,
            approval_level=ProvisioningApprovalLevel.PRODUCTION.value if is_prod else ProvisioningApprovalLevel.STANDARD.value,
            environment=environment,
            risk_level=request.risk_level,
            requires_double_approval=is_prod,
            risk_summary_snapshot_json={},
            gates_snapshot_json={},
            cost_snapshot_json={},
            security_snapshot_json={},
            plan_summary_snapshot_json={},
        )
        self.db.add(approval)
        if request.status == ProvisioningRequestStatus.READY_FOR_APPROVAL.value:
            request.status = ProvisioningRequestStatus.PENDING_APPROVAL.value
        self.db.flush()
        return approval

    def _environment(self, request: ProvisioningRequest) -> str:
        return str(
            request.input_variables.get("environment")
            or request.tfvars_json.get("environment")
            or (request.evidence or {}).get("risk_summary", {}).get("environment")
            or "dev"
        )

    def _apply_snapshots(self, approval: ProvisioningApproval, snapshots: dict[str, Any]) -> None:
        approval.risk_summary_snapshot_json = snapshots["risk_summary"]
        approval.gates_snapshot_json = snapshots["gates"]
        approval.cost_snapshot_json = snapshots["cost"]
        approval.security_snapshot_json = snapshots["security"]
        approval.plan_summary_snapshot_json = snapshots["plan_summary"]
        approval.approved_plan_checksum_sha256 = snapshots["checksums"]["plan"]
        approval.approved_plan_json_checksum_sha256 = snapshots["checksums"]["plan_json"]
        approval.approved_risk_summary_checksum_sha256 = snapshots["checksums"]["risk_summary"]
        approval.approved_gates_result_checksum_sha256 = snapshots["checksums"]["gates_result"]
