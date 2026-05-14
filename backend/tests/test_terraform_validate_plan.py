from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.orm import Session

from cloud_shell.command_executor import CloudShellExecutor
from cloud_shell.schemas import ShellUserContext
from core.database import SessionLocal
from models.provisioning_request import ProvisioningRequest
from models.tenant import Tenant
from models.user import User, UserRole
from provisioning.artifact_service import ProvisioningArtifactService, sanitize_sensitive_text
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.template_catalog import get_phase_c_execution_template
from provisioning.terraform_plan_parser import TerraformPlanParser
from provisioning.terraform_runner import TERRAFORM_NOT_FOUND, TerraformRunner
from provisioning.terraform_workspace import TerraformWorkspaceManager


def _seed_request(status: str = "DRAFT") -> tuple[Session, User, ProvisioningRequest]:
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"Terraform Tenant {suffix}", slug=f"tf-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"terraform-{suffix}@northbound.local",
        full_name="Terraform User",
        hashed_password="not-used",
        role=UserRole.ANALYST.value,
        is_active=True,
    )
    db.add(user)
    db.flush()
    request = ProvisioningRequest(
        request_number=f"REQ-{suffix[:8]}",
        created_at_sequence=1,
        tenant_id=tenant.id,
        provider="aws",
        template_key="cloud-public-exposure-review",
        template_version="v0",
        status=status,
        risk_level="HIGH",
        title="Draft remediation",
        description="Draft",
        input_variables={"resource_id": "sg-123"},
        tfvars_json={"request_code": f"REQ-{suffix[:8]}"},
        evidence={},
        approval_required=True,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return db, user, request


def test_workspace_creates_tfvars_and_blocks_path_traversal(tmp_path: Path) -> None:
    db, _, request = _seed_request()
    try:
        manager = TerraformWorkspaceManager(runtime_root=tmp_path)
        workspace = manager.prepare_workspace(
            request=request,
            template=get_phase_c_execution_template(),
            tfvars={"request_code": request.request_number},
        )

        assert workspace.tfvars_path.exists()
        assert (workspace.workspace_path / "main.tf").exists()
        assert json.loads(workspace.tfvars_path.read_text())["request_code"] == request.request_number
        try:
            manager.safe_request_code("../REQ-1")
        except ValueError:
            pass
        else:
            raise AssertionError("Path traversal request code should be rejected")
    finally:
        db.close()


def test_plan_parser_detects_destructive_changes() -> None:
    payload = {
        "terraform_version": "1.6.0",
        "resource_changes": [
            {"provider_name": "registry.terraform.io/hashicorp/aws", "change": {"actions": ["create"]}},
            {"provider_name": "registry.terraform.io/hashicorp/aws", "change": {"actions": ["delete", "create"]}},
        ],
    }

    summary = TerraformPlanParser().parse(payload)

    assert summary["add_count"] == 1
    assert summary["replace_count"] == 1
    assert summary["has_destructive_changes"] is True


def test_artifact_service_registers_file_and_blocks_outside_path(tmp_path: Path) -> None:
    db, user, request = _seed_request()
    try:
        workspace = tmp_path / request.request_number
        workspace.mkdir()
        log_path = workspace / "init.log"
        log_path.write_text("ok", encoding="utf-8")
        artifact = ProvisioningArtifactService(db).create_file_artifact(
            request=request,
            artifact_type=ProvisioningArtifactType.TERRAFORM_INIT_LOG,
            path=log_path,
            workspace_root=workspace,
            created_by_user_id=str(user.id),
        )
        assert artifact.checksum
        assert artifact.size_bytes == 2
        outside = tmp_path / "outside.log"
        outside.write_text("no", encoding="utf-8")
        try:
            ProvisioningArtifactService(db).create_file_artifact(
                request=request,
                artifact_type=ProvisioningArtifactType.TERRAFORM_INIT_LOG,
                path=outside,
                workspace_root=workspace,
            )
        except ValueError:
            pass
        else:
            raise AssertionError("Outside artifact path should be rejected")
    finally:
        db.close()


def test_terraform_runner_validate_and_plan_with_allowlisted_commands(monkeypatch, tmp_path: Path) -> None:
    db, user, request = _seed_request()
    commands: list[list[str]] = []

    def fake_run(command, **kwargs):
        commands.append(command)
        assert "shell" not in kwargs
        if command[1] == "show":
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    {
                        "terraform_version": "1.6.0",
                        "resource_changes": [{"provider_name": "terraform.io/builtin/terraform", "change": {"actions": ["create"]}}],
                    }
                ),
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    try:
        manager = TerraformWorkspaceManager(runtime_root=tmp_path)
        runner = TerraformRunner(db, workspace_manager=manager)
        validate_results = runner.validate(request, created_by_user_id=str(user.id))
        plan_results = runner.plan(request, created_by_user_id=str(user.id))

        assert validate_results["validate"].success is True
        assert plan_results["show"].plan_summary["add_count"] == 1
        assert request.status == ProvisioningRequestStatus.PLAN_READY.value
        assert ["terraform", "init", "-input=false", "-no-color"] in commands
        assert ["terraform", "validate", "-no-color"] in commands
        assert ["terraform", "plan", "-out=plan.out", "-input=false", "-no-color"] in commands
        assert ["terraform", "show", "-json", "plan.out"] in commands
    finally:
        db.close()


def test_terraform_runner_handles_missing_cli(monkeypatch, tmp_path: Path) -> None:
    db, _, request = _seed_request()

    def missing_run(command, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", missing_run)
    try:
        runner = TerraformRunner(db, workspace_manager=TerraformWorkspaceManager(runtime_root=tmp_path))
        results = runner.validate(request)

        assert results["init"].success is False
        assert results["init"].stderr == TERRAFORM_NOT_FOUND
        assert request.status == ProvisioningRequestStatus.TERRAFORM_INIT_FAILED.value
    finally:
        db.close()


def test_cloud_shell_terraform_commands(monkeypatch, tmp_path: Path) -> None:
    db, user, request = _seed_request()

    def fake_run(command, **kwargs):
        if command[1] == "show":
            return SimpleNamespace(returncode=0, stdout=json.dumps({"terraform_version": "1.6.0", "resource_changes": []}), stderr="")
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(TerraformRunner, "__init__", lambda self, db, **kwargs: setattr(self, "db", db) or setattr(self, "workspace_manager", TerraformWorkspaceManager(runtime_root=tmp_path)) or setattr(self, "artifact_service", ProvisioningArtifactService(db)) or setattr(self, "plan_parser", TerraformPlanParser()))
    try:
        context = ShellUserContext(user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        validate = CloudShellExecutor().execute(db, raw_command=f"nb terraform validate {request.request_number}", user_context=context)
        plan = CloudShellExecutor().execute(db, raw_command=f"nb terraform plan {request.request_number}", user_context=context)
        evidence = CloudShellExecutor().execute(db, raw_command=f"nb evidence show {request.request_number}", user_context=context)
        apply = CloudShellExecutor().execute(db, raw_command=f"nb terraform apply {request.request_number}", user_context=context)
        destroy = CloudShellExecutor().execute(db, raw_command=f"nb terraform destroy {request.request_number}", user_context=context)

        assert validate.status == "success"
        assert plan.status == "success"
        assert "TERRAFORM_PLAN_JSON" in evidence.output
        assert apply.status == "blocked"
        assert "No infrastructure changes were executed." in apply.output
        assert destroy.status == "blocked"
    finally:
        db.close()


def test_secret_sanitizer_redacts_sensitive_values() -> None:
    value = "AWS_SECRET_ACCESS_KEY=abc123 PASSWORD: supersecret"

    sanitized = sanitize_sensitive_text(value)

    assert "abc123" not in sanitized
    assert "supersecret" not in sanitized
    assert "[REDACTED]" in sanitized
