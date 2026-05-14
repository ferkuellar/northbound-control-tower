from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningRequest
from provisioning.artifact_service import ProvisioningArtifactService, sanitize_json, sanitize_sensitive_text
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.workspace_security import resolve_request_workspace

OUTPUT_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class OutputCaptureResult:
    success: bool
    outputs: dict[str, Any]
    exit_code: int
    stderr: str


class TerraformOutputService:
    def __init__(
        self,
        db: Session,
        *,
        artifact_service: ProvisioningArtifactService | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.db = db
        self.artifact_service = artifact_service or ProvisioningArtifactService(db)
        self.runner = runner or subprocess.run

    def capture(self, request: ProvisioningRequest, *, created_by_user_id: str | None = None) -> OutputCaptureResult:
        workspace_path = resolve_request_workspace(request)
        request.status = ProvisioningRequestStatus.OUTPUTS_CAPTURE_RUNNING.value
        self.db.flush()
        stdout = ""
        stderr = ""
        exit_code = 1
        try:
            completed = self.runner(
                ["terraform", "output", "-json"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=OUTPUT_TIMEOUT_SECONDS,
                check=False,
            )
            exit_code = completed.returncode
            stdout = completed.stdout or ""
            stderr = sanitize_sensitive_text(completed.stderr or "")
        except FileNotFoundError:
            stderr = "Terraform CLI not found."
        except subprocess.TimeoutExpired:
            stderr = f"Terraform output timed out after {OUTPUT_TIMEOUT_SECONDS} seconds."

        outputs: dict[str, Any] = {}
        if exit_code == 0:
            try:
                outputs = sanitize_json(json.loads(stdout or "{}"))
            except json.JSONDecodeError:
                stderr = "Terraform output JSON is invalid."
                exit_code = 1

        if exit_code == 0:
            self.artifact_service.create_json_file(
                request=request,
                artifact_type=ProvisioningArtifactType.TERRAFORM_OUTPUT_JSON,
                path=workspace_path / "outputs.json",
                workspace_root=workspace_path,
                payload=outputs,
                created_by_user_id=created_by_user_id,
            )
            request.status = ProvisioningRequestStatus.OUTPUTS_CAPTURED.value
            request.evidence = {**(request.evidence or {}), "terraform_outputs": {"captured": True}}
        else:
            request.status = ProvisioningRequestStatus.OUTPUTS_CAPTURE_FAILED.value
            request.evidence = {**(request.evidence or {}), "terraform_outputs": {"captured": False, "error": stderr}}
        self.db.flush()
        return OutputCaptureResult(success=exit_code == 0, outputs=outputs, exit_code=exit_code, stderr=stderr)

    def safe_rows(self, outputs: dict[str, Any]) -> list[tuple[str, str, str]]:
        rows: list[tuple[str, str, str]] = []
        for name, payload in outputs.items():
            if not isinstance(payload, dict):
                rows.append((str(name), "false", str(payload)))
                continue
            sensitive = bool(payload.get("sensitive"))
            value = "[SENSITIVE]" if sensitive else str(payload.get("value"))
            rows.append((str(name), str(sensitive).lower(), value))
        return rows
