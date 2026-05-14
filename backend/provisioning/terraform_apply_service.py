from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Callable

from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningRequest
from provisioning.apply_lock_service import ApplyLockService
from provisioning.apply_precheck_service import ApplyPrecheckResult, ApplyPrecheckService
from provisioning.artifact_service import ProvisioningArtifactService, sanitize_json, sanitize_sensitive_text
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.output_service import OutputCaptureResult, TerraformOutputService

APPLY_TIMEOUT_SECONDS = 1800
APPLY_COMMAND = ["terraform", "apply", "-input=false", "-no-color", "plan.out"]


@dataclass(frozen=True)
class TerraformApplyResult:
    precheck: ApplyPrecheckResult
    apply_executed: bool
    success: bool
    exit_code: int | None = None
    stderr: str | None = None
    outputs: OutputCaptureResult | None = None


class TerraformApplyService:
    def __init__(
        self,
        db: Session,
        *,
        artifact_service: ProvisioningArtifactService | None = None,
        precheck_service: ApplyPrecheckService | None = None,
        lock_service: ApplyLockService | None = None,
        output_service: TerraformOutputService | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.db = db
        self.artifact_service = artifact_service or ProvisioningArtifactService(db)
        self.precheck_service = precheck_service or ApplyPrecheckService(db, artifact_service=self.artifact_service)
        self.lock_service = lock_service or ApplyLockService(db)
        self.output_service = output_service or TerraformOutputService(db, artifact_service=self.artifact_service)
        self.runner = runner or subprocess.run

    def apply(self, request: ProvisioningRequest, *, created_by_user_id: str | None = None) -> TerraformApplyResult:
        precheck = self.precheck_service.run(request, created_by_user_id=created_by_user_id)
        if not precheck.passed or precheck.workspace_path is None:
            self.db.commit()
            return TerraformApplyResult(precheck=precheck, apply_executed=False, success=False, stderr="; ".join(precheck.reasons))

        lock_result = self.lock_service.acquire(request, locked_by=created_by_user_id)
        if not lock_result.acquired or lock_result.lock is None:
            request.status = ProvisioningRequestStatus.APPLY_PRECHECK_FAILED.value
            request.evidence = {**(request.evidence or {}), "apply_lock": {"acquired": False, "reason": lock_result.reason}}
            self.db.commit()
            blocked = ApplyPrecheckResult(False, request, precheck.workspace_path, precheck.approval, checks=precheck.checks, reasons=[lock_result.reason or "Apply lock unavailable"])
            return TerraformApplyResult(precheck=blocked, apply_executed=False, success=False, stderr=lock_result.reason)

        request.status = ProvisioningRequestStatus.APPLY_RUNNING.value
        self.db.flush()
        started = datetime.now(UTC)
        start_counter = perf_counter()
        stdout = ""
        stderr = ""
        exit_code = 1
        try:
            completed = self.runner(
                APPLY_COMMAND,
                cwd=precheck.workspace_path,
                env=self._safe_env(),
                capture_output=True,
                text=True,
                timeout=APPLY_TIMEOUT_SECONDS,
                check=False,
            )
            exit_code = completed.returncode
            stdout = sanitize_sensitive_text(completed.stdout or "")
            stderr = sanitize_sensitive_text(completed.stderr or "")
        except FileNotFoundError:
            stderr = "Terraform CLI not found."
        except subprocess.TimeoutExpired:
            stderr = f"Terraform apply timed out after {APPLY_TIMEOUT_SECONDS} seconds."

        finished = datetime.now(UTC)
        duration_ms = int((perf_counter() - start_counter) * 1000)
        log_path = precheck.workspace_path / "apply.log"
        log_path.write_text(
            "\n".join(
                [
                    "$ terraform apply -input=false -no-color plan.out",
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
        self.artifact_service.create_file_artifact(
            request=request,
            artifact_type=ProvisioningArtifactType.TERRAFORM_APPLY_LOG,
            path=log_path,
            workspace_root=precheck.workspace_path,
            created_by_user_id=created_by_user_id,
            content_type="text/plain",
            content_json={"exit_code": exit_code, "duration_ms": duration_ms},
        )
        metadata = {
            "command": "terraform apply -input=false -no-color plan.out",
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "duration_ms": duration_ms,
            "exit_code": exit_code,
            "success": exit_code == 0,
            "lock_token": lock_result.lock.lock_token,
        }
        self.artifact_service.create_json_file(
            request=request,
            artifact_type=ProvisioningArtifactType.TERRAFORM_APPLY_METADATA,
            path=precheck.workspace_path / "apply-metadata.json",
            workspace_root=precheck.workspace_path,
            payload=metadata,
            created_by_user_id=created_by_user_id,
        )

        outputs = None
        if exit_code == 0:
            request.status = ProvisioningRequestStatus.APPLY_SUCCEEDED.value
            request.evidence = {**(request.evidence or {}), "terraform_apply": sanitize_json(metadata)}
            self.db.flush()
            outputs = self.output_service.capture(request, created_by_user_id=created_by_user_id)
            self.lock_service.release(lock_result.lock, status="RELEASED")
            self.db.commit()
            return TerraformApplyResult(precheck=precheck, apply_executed=True, success=True, exit_code=exit_code, stderr=stderr, outputs=outputs)

        request.status = ProvisioningRequestStatus.APPLY_FAILED.value
        request.evidence = {**(request.evidence or {}), "terraform_apply": sanitize_json(metadata)}
        self.lock_service.release(lock_result.lock, status="RELEASED_WITH_ERROR", error_message=stderr)
        self.db.commit()
        return TerraformApplyResult(precheck=precheck, apply_executed=True, success=False, exit_code=exit_code, stderr=stderr)

    def _safe_env(self) -> dict[str, str]:
        allowed_keys = {"PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "TEMP", "TMP"}
        return {key: value for key, value in os.environ.items() if key.upper() in allowed_keys}
