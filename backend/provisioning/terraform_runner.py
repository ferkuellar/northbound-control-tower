from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningRequest
from provisioning.artifact_service import ProvisioningArtifactService, sanitize_json, sanitize_sensitive_text
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.template_catalog import get_phase_c_execution_template
from provisioning.terraform_plan_parser import TerraformPlanParser
from provisioning.terraform_workspace import TerraformWorkspaceManager, WorkspaceResult

TERRAFORM_TIMEOUT_SECONDS = 180
TERRAFORM_NOT_FOUND = "Terraform CLI not found. Install Terraform or use the provisioning worker image with Terraform installed."


@dataclass(frozen=True)
class TerraformCommandResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    success: bool
    artifact_paths: list[str] = field(default_factory=list)
    plan_summary: dict[str, Any] | None = None


class TerraformRunner:
    def __init__(
        self,
        db: Session,
        *,
        workspace_manager: TerraformWorkspaceManager | None = None,
        artifact_service: ProvisioningArtifactService | None = None,
        plan_parser: TerraformPlanParser | None = None,
    ) -> None:
        self.db = db
        self.workspace_manager = workspace_manager or TerraformWorkspaceManager()
        self.artifact_service = artifact_service or ProvisioningArtifactService(db)
        self.plan_parser = plan_parser or TerraformPlanParser()

    def prepare_workspace(self, request: ProvisioningRequest, *, created_by_user_id: str | None = None) -> WorkspaceResult:
        execution_template = get_phase_c_execution_template(request.template_key)
        if not execution_template.terraform_enabled:
            raise ValueError("Terraform execution template is disabled.")
        tfvars = self._tfvars_for_phase_c(request)
        workspace = self.workspace_manager.prepare_workspace(request=request, template=execution_template, tfvars=tfvars)
        request.workspace_path = str(workspace.workspace_path)
        self.artifact_service.create_file_artifact(
            request=request,
            artifact_type=ProvisioningArtifactType.TFVARS,
            path=workspace.tfvars_path,
            workspace_root=workspace.workspace_path,
            created_by_user_id=created_by_user_id,
            content_type="application/json",
            content_json=tfvars,
        )
        self.artifact_service.create_file_artifact(
            request=request,
            artifact_type=ProvisioningArtifactType.TERRAFORM_WORKSPACE_METADATA,
            path=workspace.metadata_path,
            workspace_root=workspace.workspace_path,
            created_by_user_id=created_by_user_id,
            content_type="application/json",
            content_json={
                "workspace_path": str(workspace.workspace_path),
                "execution_template_key": execution_template.key,
                "remediation_template_key": request.template_key,
            },
        )
        self.db.flush()
        return workspace

    def validate(self, request: ProvisioningRequest, *, created_by_user_id: str | None = None) -> dict[str, TerraformCommandResult]:
        workspace = self.prepare_workspace(request, created_by_user_id=created_by_user_id)
        request.status = ProvisioningRequestStatus.TERRAFORM_INIT_RUNNING.value
        self.db.flush()
        init_result = self.init(request, workspace=workspace, created_by_user_id=created_by_user_id)
        if not init_result.success:
            request.status = ProvisioningRequestStatus.TERRAFORM_INIT_FAILED.value
            self.db.commit()
            return {"init": init_result}

        request.status = ProvisioningRequestStatus.TERRAFORM_INIT_SUCCEEDED.value
        self.db.flush()
        request.status = ProvisioningRequestStatus.TERRAFORM_VALIDATE_RUNNING.value
        self.db.flush()
        validate_result = self._run_allowed_command(
            request=request,
            workspace=workspace,
            command=["terraform", "validate", "-no-color"],
            command_label="terraform validate -no-color",
            log_name="validate.log",
            artifact_type=ProvisioningArtifactType.TERRAFORM_VALIDATE_LOG,
            created_by_user_id=created_by_user_id,
        )
        request.status = (
            ProvisioningRequestStatus.TERRAFORM_VALIDATE_SUCCEEDED.value
            if validate_result.success
            else ProvisioningRequestStatus.TERRAFORM_VALIDATE_FAILED.value
        )
        if validate_result.success:
            request.evidence = {**(request.evidence or {}), "terraform_validate": "succeeded"}
        self.db.commit()
        return {"init": init_result, "validate": validate_result}

    def init(
        self,
        request: ProvisioningRequest,
        *,
        workspace: WorkspaceResult,
        created_by_user_id: str | None = None,
    ) -> TerraformCommandResult:
        return self._run_allowed_command(
            request=request,
            workspace=workspace,
            command=["terraform", "init", "-input=false", "-no-color"],
            command_label="terraform init -input=false -no-color",
            log_name="init.log",
            artifact_type=ProvisioningArtifactType.TERRAFORM_INIT_LOG,
            created_by_user_id=created_by_user_id,
        )

    def plan(self, request: ProvisioningRequest, *, created_by_user_id: str | None = None) -> dict[str, TerraformCommandResult]:
        if request.status not in {
            ProvisioningRequestStatus.TERRAFORM_VALIDATE_SUCCEEDED.value,
            ProvisioningRequestStatus.READY_FOR_PLAN.value,
            ProvisioningRequestStatus.PLAN_READY.value,
        }:
            raise ValueError("Run nb terraform validate <request_id> before planning.")
        if not request.workspace_path:
            raise ValueError("Terraform workspace is missing. Run validate first.")

        workspace = WorkspaceResult(
            workspace_path=Path(request.workspace_path),
            template_path=Path(request.workspace_path),
            tfvars_path=Path(request.workspace_path) / "terraform.tfvars.json",
            metadata_path=Path(request.workspace_path) / "execution-metadata.json",
        )
        request.status = ProvisioningRequestStatus.PLAN_RUNNING.value
        self.db.flush()
        plan_result = self._run_allowed_command(
            request=request,
            workspace=workspace,
            command=["terraform", "plan", "-out=plan.out", "-input=false", "-no-color"],
            command_label="terraform plan -out=plan.out -input=false -no-color",
            log_name="plan.log",
            artifact_type=ProvisioningArtifactType.TERRAFORM_PLAN_LOG,
            created_by_user_id=created_by_user_id,
        )
        if not plan_result.success:
            request.status = ProvisioningRequestStatus.PLAN_FAILED.value
            self.db.commit()
            return {"plan": plan_result}

        plan_out = workspace.workspace_path / "plan.out"
        if plan_out.exists():
            self.artifact_service.create_file_artifact(
                request=request,
                artifact_type=ProvisioningArtifactType.TERRAFORM_PLAN_BINARY,
                path=plan_out,
                workspace_root=workspace.workspace_path,
                created_by_user_id=created_by_user_id,
                content_type="application/octet-stream",
            )

        show_result = self.show_plan_json(request, workspace=workspace, created_by_user_id=created_by_user_id)
        request.status = ProvisioningRequestStatus.PLAN_READY.value if show_result.success else ProvisioningRequestStatus.PLAN_FAILED.value
        if show_result.plan_summary:
            request.evidence = {
                **(request.evidence or {}),
                "terraform_plan": sanitize_json(show_result.plan_summary),
            }
        self.db.commit()
        return {"plan": plan_result, "show": show_result}

    def show_plan_json(
        self,
        request: ProvisioningRequest,
        *,
        workspace: WorkspaceResult,
        created_by_user_id: str | None = None,
    ) -> TerraformCommandResult:
        result = self._run_allowed_command(
            request=request,
            workspace=workspace,
            command=["terraform", "show", "-json", "plan.out"],
            command_label="terraform show -json plan.out",
            log_name="plan.json",
            artifact_type=ProvisioningArtifactType.TERRAFORM_PLAN_JSON,
            created_by_user_id=created_by_user_id,
            write_stdout_only=True,
            content_type="application/json",
        )
        if result.success:
            try:
                summary = self.plan_parser.parse_file(workspace.workspace_path / "plan.json")
                return TerraformCommandResult(**{**result.__dict__, "plan_summary": summary})
            except ValueError as exc:
                return TerraformCommandResult(**{**result.__dict__, "success": False, "stderr": str(exc)})
        return result

    def _run_allowed_command(
        self,
        *,
        request: ProvisioningRequest,
        workspace: WorkspaceResult,
        command: list[str],
        command_label: str,
        log_name: str,
        artifact_type: ProvisioningArtifactType,
        created_by_user_id: str | None,
        write_stdout_only: bool = False,
        content_type: str = "text/plain",
    ) -> TerraformCommandResult:
        self._assert_allowed(command)
        started = datetime.now(UTC)
        started_counter = perf_counter()
        stdout = ""
        stderr = ""
        exit_code = 1
        try:
            completed = subprocess.run(
                command,
                cwd=workspace.workspace_path,
                env=self._safe_env(),
                capture_output=True,
                text=True,
                timeout=TERRAFORM_TIMEOUT_SECONDS,
                check=False,
            )
            exit_code = completed.returncode
            stdout = sanitize_sensitive_text(completed.stdout or "")
            stderr = sanitize_sensitive_text(completed.stderr or "")
        except FileNotFoundError:
            stderr = TERRAFORM_NOT_FOUND
        except subprocess.TimeoutExpired:
            stderr = f"Terraform command timed out after {TERRAFORM_TIMEOUT_SECONDS} seconds."

        finished = datetime.now(UTC)
        duration_ms = int((perf_counter() - started_counter) * 1000)
        log_path = workspace.workspace_path / log_name
        if write_stdout_only:
            log_path.write_text(stdout, encoding="utf-8")
        else:
            log_path.write_text(
                "\n".join(
                    [
                        f"$ {command_label}",
                        "",
                        "STDOUT:",
                        stdout,
                        "",
                        "STDERR:",
                        stderr,
                        "",
                        f"EXIT_CODE: {exit_code}",
                    ]
                ),
                encoding="utf-8",
            )
        artifact = self.artifact_service.create_file_artifact(
            request=request,
            artifact_type=artifact_type,
            path=log_path,
            workspace_root=workspace.workspace_path,
            created_by_user_id=created_by_user_id,
            content_type=content_type,
            content_json={
                "command": command_label,
                "exit_code": exit_code,
                "success": exit_code == 0,
                "duration_ms": duration_ms,
            },
        )
        self.db.flush()
        return TerraformCommandResult(
            command=command_label,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            started_at=started,
            finished_at=finished,
            duration_ms=duration_ms,
            success=exit_code == 0,
            artifact_paths=[artifact.storage_path or artifact.name],
        )

    def _assert_allowed(self, command: list[str]) -> None:
        allowed = {
            ("terraform", "init", "-input=false", "-no-color"),
            ("terraform", "validate", "-no-color"),
            ("terraform", "plan", "-out=plan.out", "-input=false", "-no-color"),
            ("terraform", "show", "-json", "plan.out"),
        }
        if tuple(command) not in allowed:
            raise ValueError("Terraform command is not allowlisted.")

    def _safe_env(self) -> dict[str, str]:
        allowed_keys = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TEMP", "TMP"}
        return {key: value for key, value in os.environ.items() if key.upper() in allowed_keys}

    def _tfvars_for_phase_c(self, request: ProvisioningRequest) -> dict[str, Any]:
        return {
            "request_code": request.request_number,
            "request_id": str(request.id),
            "provider": request.provider,
            "remediation_template_key": request.template_key,
            "phase": "C",
            "terraform_apply_enabled": False,
            "terraform_destroy_enabled": False,
        }
