from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from findings.enums import FindingStatus
from models.cloud_account import CloudAccount
from models.finding import Finding
from models.provisioning_request import PostRemediationValidation, ProvisioningRequest
from models.user import User
from provisioning.artifact_service import ProvisioningArtifactService, sanitize_json
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.findings_diff_service import FindingsDiffService, finding_snapshot
from provisioning.remediation_report_service import RemediationReportService
from provisioning.rescan_service import RescanResult, RescanService

ALLOWED_APPLY_STATUSES = {
    ProvisioningRequestStatus.APPLY_SUCCEEDED.value,
    ProvisioningRequestStatus.OUTPUTS_CAPTURED.value,
}

REQUEST_STATUS_BY_OUTCOME = {
    "RESOLVED": ProvisioningRequestStatus.REMEDIATION_RESOLVED.value,
    "PARTIALLY_RESOLVED": ProvisioningRequestStatus.REMEDIATION_PARTIALLY_RESOLVED.value,
    "STILL_OPEN": ProvisioningRequestStatus.REMEDIATION_STILL_OPEN.value,
    "VALIDATION_FAILED": ProvisioningRequestStatus.REMEDIATION_VALIDATION_FAILED.value,
}

FINDING_STATUS_BY_OUTCOME = {
    "RESOLVED": FindingStatus.RESOLVED.value,
    "PARTIALLY_RESOLVED": FindingStatus.PARTIALLY_RESOLVED.value,
    "STILL_OPEN": FindingStatus.STILL_OPEN.value,
    "VALIDATION_FAILED": FindingStatus.VALIDATION_FAILED.value,
}


@dataclass(frozen=True)
class PostValidationResult:
    request: ProvisioningRequest | None
    validation: PostRemediationValidation | None
    result: str
    checks: list[dict[str, str]]
    artifacts: list[str]
    success: bool
    error_message: str | None = None


class PostValidationService:
    def __init__(
        self,
        db: Session,
        *,
        rescan_service: RescanService | None = None,
        diff_service: FindingsDiffService | None = None,
        artifact_service: ProvisioningArtifactService | None = None,
        report_service: RemediationReportService | None = None,
    ) -> None:
        self.db = db
        self.artifact_service = artifact_service or ProvisioningArtifactService(db)
        self.rescan_service = rescan_service or RescanService(db)
        self.diff_service = diff_service or FindingsDiffService()
        self.report_service = report_service or RemediationReportService(db, artifact_service=self.artifact_service)

    def validate_request(self, *, tenant_id: uuid.UUID, identifier: str, user_context_user_id: str | None = None) -> PostValidationResult:
        request = self._get_request(tenant_id=tenant_id, identifier=identifier)
        user = self._get_user(user_context_user_id)
        if request is None:
            return PostValidationResult(None, None, "VALIDATION_FAILED", [], [], False, "Provisioning request not found")
        if user is None:
            return PostValidationResult(request, None, "VALIDATION_FAILED", [], [], False, "User context not found")
        if request.status not in ALLOWED_APPLY_STATUSES:
            return PostValidationResult(request, None, "VALIDATION_FAILED", [], [], False, "Request must have APPLY_SUCCEEDED before post-validation")
        if request.finding_id is None:
            return PostValidationResult(request, None, "VALIDATION_FAILED", [], [], False, "Request does not reference an original finding")
        if request.cloud_account_id is None:
            return PostValidationResult(request, None, "VALIDATION_FAILED", [], [], False, "Request does not reference a cloud account")
        workspace_path = self._workspace(request)
        if workspace_path is None:
            return PostValidationResult(request, None, "VALIDATION_FAILED", [], [], False, "Request workspace is not available")

        finding = self.db.get(Finding, request.finding_id)
        cloud_account = self.db.get(CloudAccount, request.cloud_account_id)
        if finding is None or cloud_account is None:
            return PostValidationResult(request, None, "VALIDATION_FAILED", [], [], False, "Finding or cloud account not found")

        started = datetime.now(UTC)
        timer = perf_counter()
        request.status = ProvisioningRequestStatus.POST_VALIDATION_RUNNING.value
        finding.status = FindingStatus.VALIDATING.value
        before_finding = finding_snapshot(finding)
        before_inventory = self.rescan_service.inventory_snapshot(cloud_account)
        before_findings = self.rescan_service.findings_snapshot(cloud_account)
        validation = PostRemediationValidation(
            validation_code=f"VAL-{uuid.uuid4().hex[:8]}",
            request_id=request.id,
            finding_id=finding.id,
            tenant_id=request.tenant_id,
            cloud_account_id=cloud_account.id,
            provider=request.provider,
            region=cloud_account.region or cloud_account.default_region,
            environment=(request.input_variables or {}).get("environment"),
            status="RUNNING",
            result="VALIDATION_FAILED",
            started_at=started,
            validated_by=user.id,
            before_finding_snapshot_json=before_finding,
            inventory_snapshot_before_json=before_inventory,
        )
        self.db.add(validation)
        self._write_json(request, workspace_path, ProvisioningArtifactType.FINDINGS_BEFORE_JSON, "findings-before.json", {"findings": before_findings}, user)

        rescan: RescanResult | None = None
        try:
            rescan = self.rescan_service.rescan_account(
                cloud_account=cloud_account,
                current_user=user,
                trigger_source="POST_REMEDIATION_VALIDATION",
            )
            after = self.db.get(Finding, finding.id)
            diff = self.diff_service.build_diff(
                before=self._finding_proxy(before_finding),
                after=after,
                validation_started_at=started,
                collector_succeeded=rescan.success,
                findings_engine_succeeded=rescan.findings_summary is not None and (rescan.findings_summary.rule_errors == 0),
            )
            result = diff.outcome
            validation.collector_run_id = rescan.collector_run.id
            validation.after_finding_snapshot_json = finding_snapshot(after)
            validation.inventory_snapshot_after_json = rescan.inventory_snapshot
            validation.findings_diff_json = diff.payload
            validation.validation_checks_json = diff.checks
            validation.evidence_json = {"collector_run_code": rescan.collector_run.collector_run_code}
            validation.error_message = rescan.error_message
            validation.result = result
            validation.status = "SUCCEEDED" if result != "VALIDATION_FAILED" else "FAILED"
            request.status = REQUEST_STATUS_BY_OUTCOME[result]
            if after is not None:
                after.status = FINDING_STATUS_BY_OUTCOME[result]
                after.resolved_at = datetime.now(UTC) if result == "RESOLVED" else None
            self._write_validation_artifacts(request, workspace_path, validation, rescan, user)
            self.db.flush()
            self.report_service.generate(request=request, validation=validation, workspace_path=workspace_path, created_by_user_id=str(user.id))
            request.status = REQUEST_STATUS_BY_OUTCOME[result] if result != "RESOLVED" else ProvisioningRequestStatus.REMEDIATION_RESOLVED.value
            return self._finish(validation, request, result, diff.checks, None)
        except Exception as exc:
            result = "VALIDATION_FAILED"
            validation.status = "FAILED"
            validation.result = result
            validation.error_message = str(exc)
            validation.validation_checks_json = [{"name": "validation_completed", "status": "FAIL", "message": str(exc)}]
            request.status = ProvisioningRequestStatus.REMEDIATION_VALIDATION_FAILED.value
            finding.status = FindingStatus.VALIDATION_FAILED.value
            self._write_validation_artifacts(request, workspace_path, validation, rescan, user)
            return self._finish(validation, request, result, validation.validation_checks_json, str(exc))
        finally:
            validation.finished_at = datetime.now(UTC)
            validation.duration_ms = int((perf_counter() - timer) * 1000)
            self.db.commit()

    def validate_finding(self, *, tenant_id: uuid.UUID, identifier: str, user_context_user_id: str | None = None) -> PostValidationResult:
        finding = self._get_finding(tenant_id=tenant_id, identifier=identifier)
        if finding is None:
            return PostValidationResult(None, None, "VALIDATION_FAILED", [], [], False, "Finding not found")
        request = self.db.scalar(
            select(ProvisioningRequest)
            .where(
                ProvisioningRequest.tenant_id == tenant_id,
                ProvisioningRequest.finding_id == finding.id,
                ProvisioningRequest.status.in_(ALLOWED_APPLY_STATUSES),
            )
            .order_by(ProvisioningRequest.updated_at.desc())
        )
        if request is None:
            return PostValidationResult(None, None, "VALIDATION_FAILED", [], [], False, "No applied request found for finding")
        return self.validate_request(tenant_id=tenant_id, identifier=request.request_number, user_context_user_id=user_context_user_id)

    def latest_validation(self, request: ProvisioningRequest) -> PostRemediationValidation | None:
        return self.db.scalar(
            select(PostRemediationValidation)
            .where(PostRemediationValidation.request_id == request.id)
            .order_by(PostRemediationValidation.created_at.desc())
        )

    def _finish(
        self,
        validation: PostRemediationValidation,
        request: ProvisioningRequest,
        result: str,
        checks: list[dict[str, str]],
        error_message: str | None,
    ) -> PostValidationResult:
        artifacts = [
            "post-validation-result.json",
            "post-validation-result.md",
            "findings-before.json",
            "findings-after.json",
            "findings-diff.json",
            "remediation-final-report.md",
        ]
        return PostValidationResult(request, validation, result, checks, artifacts, result != "VALIDATION_FAILED", error_message)

    def _write_validation_artifacts(
        self,
        request: ProvisioningRequest,
        workspace_path: Path,
        validation: PostRemediationValidation,
        rescan: RescanResult | None,
        user: User,
    ) -> None:
        payload = {
            "validation_code": validation.validation_code,
            "request_id": request.request_number,
            "finding_id": str(validation.finding_id) if validation.finding_id else None,
            "result": validation.result,
            "status": validation.status,
            "checks": validation.validation_checks_json,
            "error_message": validation.error_message,
        }
        self._write_json(request, workspace_path, ProvisioningArtifactType.POST_VALIDATION_RESULT_JSON, "post-validation-result.json", payload, user)
        self._write_markdown(request, workspace_path, ProvisioningArtifactType.POST_VALIDATION_RESULT_MARKDOWN, "post-validation-result.md", self._validation_markdown(request, payload), user)
        self._write_json(request, workspace_path, ProvisioningArtifactType.FINDINGS_AFTER_JSON, "findings-after.json", {"findings": rescan.findings_snapshot if rescan else []}, user)
        self._write_json(request, workspace_path, ProvisioningArtifactType.FINDINGS_DIFF_JSON, "findings-diff.json", validation.findings_diff_json, user)
        if rescan:
            self._write_json(request, workspace_path, ProvisioningArtifactType.RESCAN_INVENTORY_SNAPSHOT_JSON, "rescan-inventory-snapshot.json", rescan.inventory_snapshot, user)
            self._write_json(request, workspace_path, ProvisioningArtifactType.COLLECTOR_RUN_METADATA, "collector-run-metadata.json", rescan.collector_run.metadata_json, user)
            log = f"Collector Run: {rescan.collector_run.collector_run_code}\nStatus: {rescan.collector_run.status}\nError: {rescan.error_message or ''}\n"
            self._write_markdown(request, workspace_path, ProvisioningArtifactType.RESCAN_LOG, "rescan.log", log, user, content_type="text/plain")

    def _write_json(self, request: ProvisioningRequest, workspace_path: Path, artifact_type: ProvisioningArtifactType, name: str, payload: dict[str, Any], user: User) -> None:
        self.artifact_service.create_json_file(
            request=request,
            artifact_type=artifact_type,
            path=workspace_path / name,
            workspace_root=workspace_path,
            payload=sanitize_json(payload),
            created_by_user_id=str(user.id),
        )

    def _write_markdown(
        self,
        request: ProvisioningRequest,
        workspace_path: Path,
        artifact_type: ProvisioningArtifactType,
        name: str,
        content: str,
        user: User,
        *,
        content_type: str = "text/markdown",
    ) -> None:
        path = workspace_path / name
        path.write_text(content, encoding="utf-8")
        self.artifact_service.create_file_artifact(
            request=request,
            artifact_type=artifact_type,
            path=path,
            workspace_root=workspace_path,
            created_by_user_id=str(user.id),
            content_type=content_type,
            content_json={"name": name},
        )

    def _validation_markdown(self, request: ProvisioningRequest, payload: dict[str, Any]) -> str:
        checks = "\n".join(f"- {item['name']}: {item['status']}" for item in payload.get("checks", []))
        return f"""# Post-Remediation Validation - {request.request_number}

## Result

{payload.get("result")}

## Checks

{checks}

## Error

{payload.get("error_message") or "None"}
"""

    def _finding_proxy(self, snapshot: dict[str, Any]):
        return SimpleNamespace(
            id=uuid.UUID(snapshot["id"]) if snapshot.get("id") else None,
            cloud_account_id=uuid.UUID(snapshot["cloud_account_id"]) if snapshot.get("cloud_account_id") else None,
            resource_id=uuid.UUID(snapshot["resource_id"]) if snapshot.get("resource_id") else None,
            provider=snapshot.get("provider"),
            finding_type=snapshot.get("finding_type"),
            category=snapshot.get("category"),
            severity=snapshot.get("severity"),
            status=snapshot.get("status"),
            title=snapshot.get("title"),
            rule_id=snapshot.get("rule_id"),
            fingerprint=snapshot.get("fingerprint"),
            last_seen_at=datetime.fromisoformat(snapshot["last_seen_at"]) if snapshot.get("last_seen_at") else None,
            evidence=snapshot.get("evidence", {}),
        )

    def _workspace(self, request: ProvisioningRequest) -> Path | None:
        if not request.workspace_path:
            return None
        path = Path(request.workspace_path)
        return path if path.exists() and path.is_dir() else None

    def _get_user(self, user_id: str | None) -> User | None:
        if not user_id:
            return None
        try:
            return self.db.get(User, uuid.UUID(user_id))
        except ValueError:
            return None

    def _get_request(self, *, tenant_id: uuid.UUID, identifier: str) -> ProvisioningRequest | None:
        try:
            request_uuid = uuid.UUID(identifier)
        except ValueError:
            request_uuid = None
        statement = select(ProvisioningRequest).where(ProvisioningRequest.tenant_id == tenant_id)
        if request_uuid:
            statement = statement.where((ProvisioningRequest.id == request_uuid) | (ProvisioningRequest.request_number == identifier))
        else:
            statement = statement.where(ProvisioningRequest.request_number == identifier)
        return self.db.scalar(statement)

    def _get_finding(self, *, tenant_id: uuid.UUID, identifier: str) -> Finding | None:
        try:
            finding_uuid = uuid.UUID(identifier)
        except ValueError:
            finding_uuid = None
        statement = select(Finding).where(Finding.tenant_id == tenant_id)
        if finding_uuid:
            statement = statement.where(Finding.id == finding_uuid)
        else:
            statement = statement.where(Finding.fingerprint == identifier)
        return self.db.scalar(statement)
