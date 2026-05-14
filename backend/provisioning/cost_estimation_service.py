from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from sqlalchemy.orm import Session

from models.provisioning_request import ProvisioningRequest
from provisioning.artifact_service import ProvisioningArtifactService, sanitize_json, sanitize_sensitive_text
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.infracost_parser import InfracostParser
from provisioning.workspace_security import resolve_request_workspace

INFRACOST_TIMEOUT_SECONDS = 180
INFRACOST_NOT_FOUND = "Infracost CLI not found."
INFRACOST_API_KEY_MISSING = "INFRACOST_API_KEY is not configured."


@dataclass(frozen=True)
class CostEstimateResult:
    success: bool
    status: str
    summary: dict[str, Any]
    reason: str | None = None


class CostEstimationService:
    def __init__(
        self,
        db: Session,
        *,
        artifact_service: ProvisioningArtifactService | None = None,
        parser: InfracostParser | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ) -> None:
        self.db = db
        self.artifact_service = artifact_service or ProvisioningArtifactService(db)
        self.parser = parser or InfracostParser()
        self.runner = runner

    def estimate(self, request: ProvisioningRequest, *, created_by_user_id: str | None = None) -> CostEstimateResult:
        workspace_path = resolve_request_workspace(request)
        request.status = ProvisioningRequestStatus.COST_ESTIMATE_RUNNING.value
        self.db.flush()

        output_path = workspace_path / "infracost.json"
        started = datetime.now(UTC)
        start_counter = perf_counter()
        stdout = ""
        stderr = ""
        exit_code = 1
        reason = None
        if not os.environ.get("INFRACOST_API_KEY"):
            reason = INFRACOST_API_KEY_MISSING
            stderr = reason
        else:
            try:
                completed = self.runner(
                    [
                        "infracost",
                        "breakdown",
                        "--path",
                        str(workspace_path),
                        "--format",
                        "json",
                        "--out-file",
                        str(output_path),
                    ],
                    cwd=workspace_path,
                    capture_output=True,
                    text=True,
                    timeout=INFRACOST_TIMEOUT_SECONDS,
                    check=False,
                )
                exit_code = completed.returncode
                stdout = sanitize_sensitive_text(completed.stdout or "")
                stderr = sanitize_sensitive_text(completed.stderr or "")
            except FileNotFoundError:
                reason = INFRACOST_NOT_FOUND
                stderr = INFRACOST_NOT_FOUND
            except subprocess.TimeoutExpired:
                reason = f"Infracost timed out after {INFRACOST_TIMEOUT_SECONDS} seconds."
                stderr = reason

        summary = self._summary(output_path, reason=reason, stderr=stderr, exit_code=exit_code)
        duration_ms = int((perf_counter() - start_counter) * 1000)
        finished = datetime.now(UTC)
        self._write_artifacts(
            request=request,
            workspace_path=workspace_path,
            output_path=output_path,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
            started=started,
            finished=finished,
            summary=summary,
            created_by_user_id=created_by_user_id,
        )

        request.status = ProvisioningRequestStatus.COST_ESTIMATE_FAILED.value if reason else ProvisioningRequestStatus.COST_ESTIMATE_READY.value
        request.evidence = {**(request.evidence or {}), "cost_estimate": sanitize_json(summary)}
        self.db.commit()
        return CostEstimateResult(success=reason is None, status=request.status, summary=summary, reason=reason)

    def _summary(self, output_path: Path, *, reason: str | None, stderr: str, exit_code: int) -> dict[str, Any]:
        if reason:
            return {**self.parser.parse({}), "available": False, "reason": reason}
        if exit_code != 0 and not output_path.exists():
            return {**self.parser.parse({}), "available": False, "reason": stderr or "Infracost failed without JSON output."}
        try:
            return {**self.parser.parse_text(output_path.read_text(encoding="utf-8")), "reason": None}
        except (OSError, ValueError) as exc:
            return {**self.parser.parse({}), "available": False, "reason": str(exc)}

    def _write_artifacts(
        self,
        *,
        request: ProvisioningRequest,
        workspace_path: Path,
        output_path: Path,
        stdout: str,
        stderr: str,
        exit_code: int,
        duration_ms: int,
        started: datetime,
        finished: datetime,
        summary: dict[str, Any],
        created_by_user_id: str | None,
    ) -> None:
        if not output_path.exists():
            self.artifact_service.create_json_file(
                request=request,
                artifact_type=ProvisioningArtifactType.INFRACOST_JSON,
                path=output_path,
                workspace_root=workspace_path,
                payload={"summary": summary},
                created_by_user_id=created_by_user_id,
            )
        else:
            self.artifact_service.create_file_artifact(
                request=request,
                artifact_type=ProvisioningArtifactType.INFRACOST_JSON,
                path=output_path,
                workspace_root=workspace_path,
                created_by_user_id=created_by_user_id,
                content_type="application/json",
                content_json=summary,
            )

        log_path = workspace_path / "infracost.log"
        log_path.write_text(
            "\n".join(
                [
                    "$ infracost breakdown --path <workspace> --format json --out-file infracost.json",
                    f"started_at: {started.isoformat()}",
                    f"finished_at: {finished.isoformat()}",
                    f"duration_ms: {duration_ms}",
                    f"exit_code: {exit_code}",
                    "",
                    "STDOUT:",
                    stdout,
                    "",
                    "STDERR:",
                    stderr,
                ]
            ),
            encoding="utf-8",
        )
        self.artifact_service.create_file_artifact(
            request=request,
            artifact_type=ProvisioningArtifactType.INFRACOST_LOG,
            path=log_path,
            workspace_root=workspace_path,
            created_by_user_id=created_by_user_id,
            content_type="text/plain",
            content_json={"exit_code": exit_code, "duration_ms": duration_ms, "summary": summary},
        )
        self.db.flush()
