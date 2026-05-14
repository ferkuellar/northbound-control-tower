from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningRequest
from provisioning.artifact_service import ProvisioningArtifactService, sanitize_json, sanitize_sensitive_text
from provisioning.checkov_parser import CheckovParser
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.workspace_security import resolve_request_workspace

CHECKOV_TIMEOUT_SECONDS = 180
CHECKOV_NOT_FOUND = "Checkov CLI not found. Install Checkov in the provisioning worker image."


@dataclass(frozen=True)
class SecurityScanResult:
    success: bool
    status: str
    summary: dict[str, Any]
    reason: str | None = None


class SecurityScanService:
    def __init__(
        self,
        db: Session,
        *,
        artifact_service: ProvisioningArtifactService | None = None,
        parser: CheckovParser | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.db = db
        self.artifact_service = artifact_service or ProvisioningArtifactService(db)
        self.parser = parser or CheckovParser()
        self.runner = runner

    def scan(self, request: ProvisioningRequest, *, created_by_user_id: str | None = None) -> SecurityScanResult:
        workspace_path = resolve_request_workspace(request)
        request.status = ProvisioningRequestStatus.SECURITY_SCAN_RUNNING.value
        self.db.flush()

        started = datetime.now(UTC)
        start_counter = perf_counter()
        stdout = ""
        stderr = ""
        exit_code = 1
        reason = None
        try:
            completed = self.runner(
                ["checkov", "-d", str(workspace_path), "-o", "json"],
                cwd=workspace_path,
                capture_output=True,
                text=True,
                timeout=CHECKOV_TIMEOUT_SECONDS,
                check=False,
            )
            exit_code = completed.returncode
            stdout = sanitize_sensitive_text(completed.stdout or "")
            stderr = sanitize_sensitive_text(completed.stderr or "")
        except FileNotFoundError:
            reason = CHECKOV_NOT_FOUND
            stderr = CHECKOV_NOT_FOUND
        except subprocess.TimeoutExpired:
            reason = f"Checkov timed out after {CHECKOV_TIMEOUT_SECONDS} seconds."
            stderr = reason

        duration_ms = int((perf_counter() - start_counter) * 1000)
        finished = datetime.now(UTC)
        summary = self._parse_summary(stdout, reason=reason)
        self._write_artifacts(
            request=request,
            workspace_path=workspace_path,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
            started=started,
            finished=finished,
            summary=summary,
            created_by_user_id=created_by_user_id,
        )

        if reason or summary.get("reason"):
            request.status = ProvisioningRequestStatus.SECURITY_SCAN_FAILED.value
        elif summary["blocking_findings_count"] > 0 or summary["highest_severity"] == "CRITICAL":
            request.status = ProvisioningRequestStatus.SECURITY_SCAN_BLOCKED.value
        else:
            request.status = ProvisioningRequestStatus.SECURITY_SCAN_PASSED.value

        request.evidence = {**(request.evidence or {}), "security_scan": sanitize_json(summary)}
        self.db.commit()
        return SecurityScanResult(success=reason is None, status=request.status, summary=summary, reason=reason)

    def _parse_summary(self, stdout: str, *, reason: str | None) -> dict[str, Any]:
        if reason:
            return {**self.parser.parse({}), "tool_available": False, "reason": reason}
        try:
            return {**self.parser.parse_text(stdout), "tool_available": True, "reason": None}
        except ValueError as exc:
            return {**self.parser.parse({}), "tool_available": True, "reason": str(exc)}

    def _write_artifacts(
        self,
        *,
        request: ProvisioningRequest,
        workspace_path: Path,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_ms: int,
        started: datetime,
        finished: datetime,
        summary: dict[str, Any],
        created_by_user_id: str | None,
    ) -> None:
        json_path = workspace_path / "checkov.json"
        if stdout.strip():
            json_path.write_text(stdout, encoding="utf-8")
        else:
            self.artifact_service.create_json_file(
                request=request,
                artifact_type=ProvisioningArtifactType.CHECKOV_JSON,
                path=json_path,
                workspace_root=workspace_path,
                payload={"results": {}, "summary": summary},
                created_by_user_id=created_by_user_id,
            )
            json_created = True
        if not locals().get("json_created"):
            self.artifact_service.create_file_artifact(
                request=request,
                artifact_type=ProvisioningArtifactType.CHECKOV_JSON,
                path=json_path,
                workspace_root=workspace_path,
                created_by_user_id=created_by_user_id,
                content_type="application/json",
                content_json=summary,
            )

        log_path = workspace_path / "checkov.log"
        log_path.write_text(
            "\n".join(
                [
                    "$ checkov -d <workspace> -o json",
                    f"started_at: {started.isoformat()}",
                    f"finished_at: {finished.isoformat()}",
                    f"duration_ms: {duration_ms}",
                    f"exit_code: {exit_code}",
                    "",
                    "STDERR:",
                    stderr,
                ]
            ),
            encoding="utf-8",
        )
        self.artifact_service.create_file_artifact(
            request=request,
            artifact_type=ProvisioningArtifactType.CHECKOV_LOG,
            path=log_path,
            workspace_root=workspace_path,
            created_by_user_id=created_by_user_id,
            content_type="text/plain",
            content_json={"exit_code": exit_code, "duration_ms": duration_ms, "summary": summary},
        )
        self.db.flush()
