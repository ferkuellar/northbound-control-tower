from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from cloud_shell.command_executor import CloudShellExecutor
from cloud_shell.schemas import ShellUserContext
from core.database import SessionLocal
from models.provisioning_request import ProvisioningApproval, ProvisioningArtifact, ProvisioningExecutionLock, ProvisioningRequest
from models.tenant import Tenant
from models.user import User
from provisioning.apply_lock_service import ApplyLockService
from provisioning.apply_precheck_service import ApplyPrecheckService
from provisioning.checksum_service import ChecksumService
from provisioning.enums import ProvisioningApprovalDecision, ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.output_service import TerraformOutputService
from provisioning.terraform_apply_service import APPLY_COMMAND, TerraformApplyService


class FakeArtifactService:
    def __init__(self) -> None:
        self.artifacts: list[tuple[str, str]] = []

    def create_json_file(self, *, artifact_type, path: Path, payload, **kwargs):
        path.write_text(json.dumps(payload), encoding="utf-8")
        self.artifacts.append((artifact_type.value, path.name))
        return SimpleNamespace(storage_path=str(path), name=path.name)

    def create_file_artifact(self, *, artifact_type, path: Path, **kwargs):
        self.artifacts.append((artifact_type.value, path.name))
        return SimpleNamespace(storage_path=str(path), name=path.name)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _workspace(tmp_path: Path, *, destructive: bool = False) -> tuple[Path, dict[str, Any]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    plan_summary = {
        "resource_changes_count": 1,
        "add_count": 0 if destructive else 1,
        "change_count": 0,
        "delete_count": 1 if destructive else 0,
        "replace_count": 0,
        "has_destructive_changes": destructive,
    }
    (tmp_path / "plan.out").write_bytes(b"approved-plan")
    (tmp_path / "plan.json").write_text(json.dumps(plan_summary), encoding="utf-8")
    (tmp_path / "risk-summary.json").write_text(json.dumps({"terraform": plan_summary}), encoding="utf-8")
    (tmp_path / "gates-result.json").write_text(
        json.dumps({"decision": "READY_FOR_APPROVAL", "blocked": False, "plan_summary": plan_summary}),
        encoding="utf-8",
    )
    return tmp_path, plan_summary


def _user() -> tuple[Any, User]:
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"Apply Tenant {suffix}", slug=f"apply-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"apply-{suffix}@northbound.local",
        full_name="Apply User",
        hashed_password="not-used",
        role="ADMIN",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user


def _approved_request(db, user: User, workspace: Path, plan_summary: dict[str, Any], *, status: str = ProvisioningRequestStatus.APPROVED.value) -> ProvisioningRequest:
    request = ProvisioningRequest(
        request_number=f"REQ-{uuid.uuid4().hex[:8]}",
        tenant_id=user.tenant_id,
        cloud_account_id=None,
        finding_id=None,
        requested_by_user_id=user.id,
        provider="local",
        template_key="local-noop-validation",
        template_version="v0",
        status=status,
        risk_level="LOW",
        title="Apply test",
        description="Apply test",
        input_variables={"environment": "dev"},
        tfvars_json={},
        workspace_path=str(workspace),
        evidence={"terraform_plan": plan_summary, "policy_gates": {"blocked": False, "decision": "READY_FOR_APPROVAL"}, "approval": {"decision": "APPROVED"}},
        approval_required=True,
    )
    db.add(request)
    db.flush()
    artifacts = [
        (ProvisioningArtifactType.TERRAFORM_PLAN_BINARY, "plan.out", {}),
        (ProvisioningArtifactType.TERRAFORM_PLAN_JSON, "plan.json", plan_summary),
        (ProvisioningArtifactType.RISK_SUMMARY_JSON, "risk-summary.json", {"terraform": plan_summary}),
        (ProvisioningArtifactType.GATES_RESULT_JSON, "gates-result.json", {"blocked": False, "decision": "READY_FOR_APPROVAL", "plan_summary": plan_summary}),
    ]
    checksums = {}
    for artifact_type, name, content in artifacts:
        checksum = _sha(workspace / name)
        checksums[name] = checksum
        db.add(
            ProvisioningArtifact(
                tenant_id=request.tenant_id,
                provisioning_request_id=request.id,
                artifact_type=artifact_type.value,
                name=name,
                storage_path=str(workspace / name),
                content_json=content,
                checksum=checksum,
            )
        )
    db.add(
        ProvisioningApproval(
            approval_code=f"APP-{uuid.uuid4().hex[:8]}",
            request_id=request.id,
            tenant_id=request.tenant_id,
            requested_by=user.id,
            approved_by=user.id,
            decision=ProvisioningApprovalDecision.APPROVED.value,
            status=ProvisioningApprovalDecision.APPROVED.value,
            approval_level="STANDARD",
            environment="dev",
            risk_level="LOW",
            requires_double_approval=False,
            approval_note="approved",
            risk_summary_snapshot_json={"terraform": plan_summary},
            gates_snapshot_json={"blocked": False, "decision": "READY_FOR_APPROVAL", "plan_summary": plan_summary},
            cost_snapshot_json={},
            security_snapshot_json={"highest_severity": "UNKNOWN"},
            plan_summary_snapshot_json=plan_summary,
            approved_plan_checksum_sha256=checksums["plan.out"],
            approved_plan_json_checksum_sha256=checksums["plan.json"],
            approved_risk_summary_checksum_sha256=checksums["risk-summary.json"],
            approved_gates_result_checksum_sha256=checksums["gates-result.json"],
            decided_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.refresh(request)
    return request


def test_checksum_service_detects_change_missing_and_path_escape(tmp_path: Path) -> None:
    path = tmp_path / "plan.out"
    path.write_text("a", encoding="utf-8")
    service = ChecksumService()

    first = service.sha256_file(path, workspace_root=tmp_path)
    path.write_text("b", encoding="utf-8")
    assert service.sha256_file(path, workspace_root=tmp_path) != first
    try:
        service.sha256_file(tmp_path / "missing", workspace_root=tmp_path)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("missing file should fail")
    try:
        service.sha256_file(tmp_path.parent / "outside", workspace_root=tmp_path)
    except ValueError:
        pass
    else:
        raise AssertionError("outside workspace should fail")


def test_apply_lock_acquire_duplicate_release_and_expire() -> None:
    db, user = _user()
    try:
        workspace, plan = _workspace(Path("/tmp") / f"nct-lock-{uuid.uuid4().hex}")
        workspace.mkdir(parents=True, exist_ok=True)
        request = _approved_request(db, user, workspace, plan)
        service = ApplyLockService(db)
        first = service.acquire(request, locked_by=str(user.id))
        second = service.acquire(request, locked_by=str(user.id))
        assert first.acquired is True
        assert second.acquired is False
        service.release(first.lock)
        third = service.acquire(request, locked_by=str(user.id))
        assert third.acquired is True
        third.lock.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.flush()
        fourth = service.acquire(request, locked_by=str(user.id))
        assert fourth.acquired is True
    finally:
        db.close()


def test_apply_precheck_blocks_invalid_and_passes_valid(monkeypatch, tmp_path: Path) -> None:
    db, user = _user()
    try:
        workspace, plan = _workspace(tmp_path)
        request = _approved_request(db, user, workspace, plan)
        monkeypatch.setattr("provisioning.apply_precheck_service.resolve_request_workspace", lambda request: workspace)
        result = ApplyPrecheckService(db, artifact_service=FakeArtifactService()).run(request, created_by_user_id=str(user.id))
        assert result.passed is True

        request.status = ProvisioningRequestStatus.APPROVED.value
        (workspace / "plan.out").write_bytes(b"changed")
        mismatch = ApplyPrecheckService(db, artifact_service=FakeArtifactService()).run(request, created_by_user_id=str(user.id))
        assert mismatch.passed is False
        assert any("verified" in check["message"] for check in result.checks)
    finally:
        db.close()


def test_apply_precheck_blocks_destructive(monkeypatch, tmp_path: Path) -> None:
    db, user = _user()
    try:
        workspace, plan = _workspace(tmp_path, destructive=True)
        request = _approved_request(db, user, workspace, plan)
        monkeypatch.setattr("provisioning.apply_precheck_service.resolve_request_workspace", lambda request: workspace)
        result = ApplyPrecheckService(db, artifact_service=FakeArtifactService()).run(request, created_by_user_id=str(user.id))
        assert result.passed is False
        assert any("destructive" in reason for reason in result.reasons)
    finally:
        db.close()


def test_terraform_apply_service_runs_allowed_command_and_captures_outputs(monkeypatch, tmp_path: Path) -> None:
    db, user = _user()
    try:
        workspace, plan = _workspace(tmp_path)
        request = _approved_request(db, user, workspace, plan)
        artifacts = FakeArtifactService()

        def fake_apply(command, **kwargs):
            assert command == APPLY_COMMAND
            assert "-auto-approve" not in command
            assert "shell" not in kwargs
            return subprocess.CompletedProcess(command, 0, stdout="applied", stderr="")

        def fake_output(command, **kwargs):
            assert command == ["terraform", "output", "-json"]
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"request_code": {"sensitive": False, "value": request.request_number}, "redacted_secret": {"sensitive": True, "value": "secret"}}),
                stderr="",
            )

        monkeypatch.setattr("provisioning.apply_precheck_service.resolve_request_workspace", lambda request: workspace)
        monkeypatch.setattr("provisioning.output_service.resolve_request_workspace", lambda request: workspace)
        output_service = TerraformOutputService(db, artifact_service=artifacts, runner=fake_output)
        result = TerraformApplyService(db, artifact_service=artifacts, output_service=output_service, runner=fake_apply).apply(request, created_by_user_id=str(user.id))

        assert result.success is True
        assert result.outputs and result.outputs.success
        assert ("TERRAFORM_APPLY_LOG", "apply.log") in artifacts.artifacts
        assert ("TERRAFORM_APPLY_METADATA", "apply-metadata.json") in artifacts.artifacts
        assert ("TERRAFORM_OUTPUT_JSON", "outputs.json") in artifacts.artifacts
        assert request.status == ProvisioningRequestStatus.OUTPUTS_CAPTURED.value
        active = db.query(ProvisioningExecutionLock).filter_by(request_id=request.id, status="ACTIVE").first()
        assert active is None
    finally:
        db.close()


def test_output_service_redacts_sensitive_rows() -> None:
    rows = TerraformOutputService(None).safe_rows({"token": {"sensitive": True, "value": "secret"}, "name": {"sensitive": False, "value": "demo"}})

    assert ("token", "true", "[SENSITIVE]") in rows
    assert ("name", "false", "demo") in rows


def test_cloud_shell_apply_and_outputs_commands(monkeypatch, tmp_path: Path) -> None:
    db, user = _user()
    try:
        workspace, plan = _workspace(tmp_path)
        request = _approved_request(db, user, workspace, plan)
        context = ShellUserContext(user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role)

        def fake_apply(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, stdout="applied", stderr="")

        def fake_output(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"request_code": {"sensitive": False, "value": request.request_number}}), stderr="")

        monkeypatch.setattr("provisioning.apply_precheck_service.resolve_request_workspace", lambda request: workspace)
        monkeypatch.setattr("provisioning.output_service.resolve_request_workspace", lambda request: workspace)
        monkeypatch.setattr("provisioning.terraform_apply_service.subprocess.run", fake_apply)
        monkeypatch.setattr("provisioning.output_service.subprocess.run", fake_output)

        apply_response = CloudShellExecutor().execute(db, raw_command=f"nb terraform apply {request.request_number}", user_context=context)
        outputs_response = CloudShellExecutor().execute(db, raw_command=f"nb outputs show {request.request_number}", user_context=context)
        destroy_response = CloudShellExecutor().execute(db, raw_command=f"nb terraform destroy {request.request_number}", user_context=context)

        assert apply_response.status == "success"
        assert "Apply completed successfully" in apply_response.output
        assert "request_code" in outputs_response.output
        assert destroy_response.status == "blocked"
    finally:
        db.close()
