from __future__ import annotations

import uuid
from typing import Any

from cloud_shell.command_executor import CloudShellExecutor
from cloud_shell.command_parser import CommandParser
from cloud_shell.schemas import ShellUserContext
from core.database import SessionLocal
from models.provisioning_request import ProvisioningArtifact, ProvisioningRequest
from models.tenant import Tenant
from models.user import User, UserRole
from provisioning.approval_service import ApprovalService
from provisioning.approval_validators import ApprovalValidator
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus


def _user(role: str = "APPROVER") -> tuple[Any, User]:
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"Approval Tenant {suffix}", slug=f"approval-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"approval-{role.lower()}-{suffix}@northbound.local",
        full_name="Approval User",
        hashed_password="not-used",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user


def _request(db, user: User, *, status: str = ProvisioningRequestStatus.READY_FOR_APPROVAL.value, destructive: bool = False) -> ProvisioningRequest:
    request = ProvisioningRequest(
        request_number=f"REQ-{uuid.uuid4().hex[:8]}",
        tenant_id=user.tenant_id,
        cloud_account_id=None,
        finding_id=None,
        requested_by_user_id=user.id,
        provider="AWS",
        template_key="local-noop-validation",
        template_version="v0",
        status=status,
        risk_level="LOW",
        title="Approval test",
        description="Approval test",
        input_variables={"environment": "dev"},
        tfvars_json={},
        workspace_path=None,
        evidence={
            "terraform_plan": {
                "add_count": 1,
                "change_count": 0,
                "delete_count": 1 if destructive else 0,
                "replace_count": 0,
                "has_destructive_changes": destructive,
            },
            "security_scan": {"failed_count": 0, "blocking_findings_count": 0, "highest_severity": "UNKNOWN"},
            "cost_estimate": {"currency": "USD", "total_monthly_cost": "0.00", "diff_total_monthly_cost": "0.00"},
            "risk_summary": {"environment": "dev"},
            "policy_gates": {"decision": "READY_FOR_APPROVAL", "blocked": False},
        },
        approval_required=True,
    )
    db.add(request)
    db.flush()
    _artifact(db, request, ProvisioningArtifactType.TERRAFORM_PLAN_JSON, "plan.json", request.evidence["terraform_plan"])
    _artifact(db, request, ProvisioningArtifactType.TERRAFORM_PLAN_BINARY, "plan.out", {})
    _artifact(db, request, ProvisioningArtifactType.RISK_SUMMARY_JSON, "risk-summary.json", {"terraform": request.evidence["terraform_plan"]})
    _artifact(db, request, ProvisioningArtifactType.GATES_RESULT_JSON, "gates-result.json", request.evidence["policy_gates"])
    db.commit()
    db.refresh(request)
    return request


def _artifact(db, request: ProvisioningRequest, artifact_type: ProvisioningArtifactType, name: str, content: dict[str, Any]) -> None:
    db.add(
        ProvisioningArtifact(
            tenant_id=request.tenant_id,
            provisioning_request_id=request.id,
            artifact_type=artifact_type.value,
            name=name,
            content_json=content,
            checksum=uuid.uuid4().hex,
        )
    )


def _context(user: User) -> ShellUserContext:
    return ShellUserContext(user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role)


def test_approval_validator_rejects_invalid_states_and_missing_artifacts() -> None:
    db, user = _user()
    try:
        validator = ApprovalValidator(db)
        missing = validator.validate_approve(None, _context(user))
        assert missing.allowed is False

        cancelled = _request(db, user, status=ProvisioningRequestStatus.CANCELLED.value)
        assert validator.validate_approve(cancelled, _context(user)).allowed is False

        blocked = _request(db, user, status=ProvisioningRequestStatus.GATES_BLOCKED.value)
        assert validator.validate_approve(blocked, _context(user)).allowed is False

        no_artifacts = _request(db, user)
        db.query(ProvisioningArtifact).filter_by(provisioning_request_id=no_artifacts.id).delete()
        db.commit()
        result = validator.validate_approve(no_artifacts, _context(user))
        assert result.allowed is False
        assert any("plan artifact" in reason for reason in result.reasons)
    finally:
        db.close()


def test_approval_validator_accepts_ready_request_and_blocks_destructive() -> None:
    db, user = _user()
    try:
        validator = ApprovalValidator(db)
        ready = _request(db, user)
        destructive = _request(db, user, destructive=True)

        assert validator.validate_approve(ready, _context(user)).allowed is True
        result = validator.validate_approve(destructive, _context(user))
        assert result.allowed is False
        assert any("destructive" in reason for reason in result.reasons)
    finally:
        db.close()


def test_approval_service_lists_approves_rejects_and_saves_snapshots() -> None:
    db, approver = _user()
    try:
        request = _request(db, approver)
        pending = ApprovalService(db).list_pending(tenant_id=approver.tenant_id)
        assert request.id in {item.id for item in pending}

        result = ApprovalService(db).approve(
            tenant_id=approver.tenant_id,
            identifier=request.request_number,
            note="Reviewed security, cost and gates",
            user_context=_context(approver),
        )
        assert result.request.status == ProvisioningRequestStatus.APPROVED.value
        assert result.approval.approval_note == "Reviewed security, cost and gates"
        assert result.approval.risk_summary_snapshot_json
        assert result.approval.gates_snapshot_json
        assert result.approval.approved_plan_json_checksum_sha256
        try:
            ApprovalService(db).approve(
                tenant_id=approver.tenant_id,
                identifier=request.request_number,
                note="second approval",
                user_context=_context(approver),
            )
        except ValueError as exc:
            assert "APPROVED" in str(exc)
        else:
            raise AssertionError("Request should not be approved twice")

        second = _request(db, approver)
        rejected = ApprovalService(db).reject(
            tenant_id=approver.tenant_id,
            identifier=second.request_number,
            note="Cost too high",
            user_context=_context(approver),
        )
        assert rejected.request.status == ProvisioningRequestStatus.REJECTED.value
        assert rejected.approval.rejection_reason == "Cost too high"
    finally:
        db.close()


def test_rbac_for_approval_service() -> None:
    db, approver = _user()
    _, viewer = _user(UserRole.VIEWER.value)
    try:
        request = _request(db, approver)
        for role in (UserRole.VIEWER.value, UserRole.ANALYST.value):
            context = ShellUserContext(user_id=str(viewer.id), tenant_id=str(approver.tenant_id), role=role)
            try:
                ApprovalService(db).approve(tenant_id=approver.tenant_id, identifier=request.request_number, note="nope", user_context=context)
            except ValueError as exc:
                assert "APPROVER or ADMIN" in str(exc)
            else:
                raise AssertionError(f"{role} should not approve")
    finally:
        db.close()


def test_cloud_shell_approval_commands_and_apply_destroy_guards() -> None:
    db, approver = _user()
    try:
        request = _request(db, approver)
        context = _context(approver)

        list_response = CloudShellExecutor().execute(db, raw_command="nb approvals list", user_context=context)
        show_response = CloudShellExecutor().execute(db, raw_command=f"nb approvals show {request.request_number}", user_context=context)
        approve_response = CloudShellExecutor().execute(
            db,
            raw_command=f'nb approve {request.request_number} --note "Reviewed security, cost and gates"',
            user_context=context,
        )
        apply_response = CloudShellExecutor().execute(db, raw_command=f"nb terraform apply {request.request_number}", user_context=context)
        destroy_response = CloudShellExecutor().execute(db, raw_command=f"nb terraform destroy {request.request_number}", user_context=context)

        assert "Pending Approvals" in list_response.output
        assert "Approval Detail" in show_response.output
        assert approve_response.status == "success"
        assert "APPROVED" in approve_response.output
        assert apply_response.status == "blocked"
        assert "Apply blocked" in apply_response.output
        assert "No infrastructure changes were executed." in apply_response.output
        assert destroy_response.status == "blocked"
    finally:
        db.close()


def test_parser_handles_group_only_approval_commands() -> None:
    parsed = CommandParser().parse('nb approve REQ-1001 --note "Reviewed"')

    assert parsed.group == "approve"
    assert parsed.action is None
    assert parsed.args == ["REQ-1001"]
    assert parsed.flags["note"] == "Reviewed"
