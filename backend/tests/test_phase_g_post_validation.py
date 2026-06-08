from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy.orm import Session

from cloud_shell.command_executor import CloudShellExecutor
from cloud_shell.schemas import ShellUserContext
from core.database import SessionLocal
from findings.enums import FindingStatus
from models.cloud_account import CloudAccount, CloudAccountAuthType, CloudProvider
from models.finding import Finding
from models.inventory_scan import InventoryScan, InventoryScanStatus
from models.provisioning_request import ProvisioningArtifact, ProvisioningRequest
from models.resource import Resource
from models.tenant import Tenant
from models.user import User, UserRole
from provisioning.enums import ProvisioningArtifactType, ProvisioningRequestStatus
from provisioning.findings_diff_service import FindingsDiffService
from provisioning.post_validation_service import PostValidationService
from provisioning.rescan_service import RescanService


def _seed(tmp_path: Path, *, request_status: str = ProvisioningRequestStatus.OUTPUTS_CAPTURED.value) -> tuple[Session, User, CloudAccount, Finding, ProvisioningRequest]:
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    tenant = Tenant(name=f"Phase G {suffix}", slug=f"phase-g-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"phase-g-{suffix}@northbound.local",
        full_name="Phase G User",
        hashed_password="not-used",
        role=UserRole.ADMIN.value,
        is_active=True,
    )
    account = CloudAccount(
        tenant_id=tenant.id,
        provider=CloudProvider.AWS.value,
        name=f"AWS-{suffix}",
        account_id=f"AWS-{suffix}",
        auth_type=CloudAccountAuthType.ACCESS_KEYS.value,
        default_region="us-east-1",
        is_active=True,
    )
    db.add_all([user, account])
    db.flush()
    resource = Resource(
        tenant_id=tenant.id,
        cloud_account_id=account.id,
        provider=CloudProvider.AWS.value,
        resource_type="object_storage",
        resource_id=f"arn:aws:s3:::bucket-{suffix}",
        name=f"bucket-{suffix}",
        fingerprint=uuid.uuid4().hex,
    )
    db.add(resource)
    db.flush()
    finding = Finding(
        tenant_id=tenant.id,
        cloud_account_id=account.id,
        resource_id=resource.id,
        provider=CloudProvider.AWS.value,
        finding_type="public_exposure",
        category="security",
        severity="high",
        status=FindingStatus.OPEN.value,
        title="S3 bucket public",
        description="Bucket is public",
        evidence={"public": True},
        recommendation="Block public access",
        rule_id="S3_PUBLIC_ACCESS",
        fingerprint=uuid.uuid4().hex,
        last_seen_at=datetime.now(UTC) - timedelta(minutes=10),
    )
    db.add(finding)
    db.flush()
    workspace = tmp_path / f"REQ-{suffix}"
    workspace.mkdir()
    request = ProvisioningRequest(
        request_number=f"REQ-{suffix}",
        tenant_id=tenant.id,
        cloud_account_id=account.id,
        finding_id=finding.id,
        requested_by_user_id=user.id,
        provider=CloudProvider.AWS.value,
        template_key="local-noop-validation",
        template_version="v0",
        status=request_status,
        risk_level="LOW",
        title="Phase G request",
        description="Phase G request",
        input_variables={"environment": "dev"},
        tfvars_json={},
        workspace_path=str(workspace),
        evidence={"terraform_apply": {"success": True}},
        approval_required=True,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return db, user, account, finding, request


class FakeCollectorAdapter:
    def __init__(self, *, failed: bool = False) -> None:
        self.failed = failed

    def run_inventory(self, db: Session, *, cloud_account: CloudAccount, current_user: User) -> InventoryScan:
        scan = InventoryScan(
            tenant_id=cloud_account.tenant_id,
            cloud_account_id=cloud_account.id,
            provider=cloud_account.provider,
            status=InventoryScanStatus.FAILED.value if self.failed else InventoryScanStatus.COMPLETED.value,
            resources_discovered=0 if self.failed else 1,
            error_message="expired credentials" if self.failed else None,
            created_by_user_id=current_user.id,
        )
        db.add(scan)
        db.flush()
        return scan


class FakeFindingsEngine:
    def __init__(self, *, mode: str, finding: Finding) -> None:
        self.mode = mode
        self.finding = finding

    def run(self, **kwargs):
        if self.mode == "still_open":
            self.finding.last_seen_at = datetime.now(UTC)
        if self.mode == "partial":
            self.finding.last_seen_at = datetime.now(UTC)
            self.finding.severity = "medium"
        return SimpleNamespace(findings_created=0, findings_updated=1, rule_errors=0)


def _service(db: Session, finding: Finding, *, mode: str = "resolved", failed_collector: bool = False) -> PostValidationService:
    rescan = RescanService(db, collector_adapter=FakeCollectorAdapter(failed=failed_collector), findings_engine=FakeFindingsEngine(mode=mode, finding=finding))
    return PostValidationService(db, rescan_service=rescan)


def test_findings_diff_detects_resolved_still_open_and_partial() -> None:
    before = SimpleNamespace(id=uuid.uuid4(), cloud_account_id=uuid.uuid4(), resource_id=uuid.uuid4(), provider="aws", finding_type="x", category="security", severity="high", status="open", title="x", rule_id="RULE", fingerprint="abc", last_seen_at=datetime.now(UTC) - timedelta(minutes=5), evidence={})
    old_after = SimpleNamespace(**before.__dict__)
    current_after = SimpleNamespace(**before.__dict__)
    current_after.last_seen_at = datetime.now(UTC)
    partial_after = SimpleNamespace(**current_after.__dict__)
    partial_after.severity = "medium"
    service = FindingsDiffService()

    assert service.build_diff(before=before, after=old_after, validation_started_at=datetime.now(UTC) - timedelta(seconds=5), collector_succeeded=True, findings_engine_succeeded=True).outcome == "RESOLVED"
    assert service.build_diff(before=before, after=current_after, validation_started_at=datetime.now(UTC) - timedelta(seconds=5), collector_succeeded=True, findings_engine_succeeded=True).outcome == "STILL_OPEN"
    assert service.build_diff(before=before, after=partial_after, validation_started_at=datetime.now(UTC) - timedelta(seconds=5), collector_succeeded=True, findings_engine_succeeded=True).outcome == "PARTIALLY_RESOLVED"


def test_post_validation_blocks_without_apply(tmp_path: Path) -> None:
    db, user, _, finding, request = _seed(tmp_path, request_status=ProvisioningRequestStatus.APPROVED.value)
    try:
        result = _service(db, finding).validate_request(tenant_id=user.tenant_id, identifier=request.request_number, user_context_user_id=str(user.id))

        assert result.success is False
        assert "APPLY_SUCCEEDED" in (result.error_message or "")
    finally:
        db.close()


def test_post_validation_marks_resolved_and_writes_artifacts(tmp_path: Path) -> None:
    db, user, _, finding, request = _seed(tmp_path)
    try:
        result = _service(db, finding, mode="resolved").validate_request(tenant_id=user.tenant_id, identifier=request.request_number, user_context_user_id=str(user.id))
        artifacts = {artifact.artifact_type for artifact in db.query(ProvisioningArtifact).filter_by(provisioning_request_id=request.id).all()}

        assert result.result == "RESOLVED"
        assert request.status == ProvisioningRequestStatus.REMEDIATION_RESOLVED.value
        assert finding.status == FindingStatus.RESOLVED.value
        assert ProvisioningArtifactType.POST_VALIDATION_RESULT_JSON.value in artifacts
        assert ProvisioningArtifactType.REMEDIATION_FINAL_REPORT_MARKDOWN.value in artifacts
    finally:
        db.close()


def test_post_validation_marks_still_open_partial_and_failed(tmp_path: Path) -> None:
    db, user, _, finding, request = _seed(tmp_path)
    try:
        still_open = _service(db, finding, mode="still_open").validate_request(tenant_id=user.tenant_id, identifier=request.request_number, user_context_user_id=str(user.id))
        assert still_open.result == "STILL_OPEN"

        request.status = ProvisioningRequestStatus.OUTPUTS_CAPTURED.value
        finding.status = FindingStatus.OPEN.value
        finding.severity = "high"
        db.commit()
        partial = _service(db, finding, mode="partial").validate_request(tenant_id=user.tenant_id, identifier=request.request_number, user_context_user_id=str(user.id))
        assert partial.result == "PARTIALLY_RESOLVED"

        request.status = ProvisioningRequestStatus.OUTPUTS_CAPTURED.value
        finding.status = FindingStatus.OPEN.value
        db.commit()
        failed = _service(db, finding, failed_collector=True).validate_request(tenant_id=user.tenant_id, identifier=request.request_number, user_context_user_id=str(user.id))
        assert failed.result == "VALIDATION_FAILED"
        assert finding.status == FindingStatus.VALIDATION_FAILED.value
    finally:
        db.close()


def test_cloud_shell_phase_g_commands(monkeypatch, tmp_path: Path) -> None:
    db, user, account, finding, request = _seed(tmp_path)
    context = ShellUserContext(user_id=str(user.id), tenant_id=str(user.tenant_id), role=UserRole.ADMIN.value)
    real_result = _service(db, finding).validate_request(tenant_id=user.tenant_id, identifier=request.request_number, user_context_user_id=str(user.id))

    class FakePostValidationService:
        def __init__(self, db):
            pass

        def validate_request(self, *, tenant_id, identifier, user_context_user_id=None):
            return real_result

    monkeypatch.setattr("cloud_shell.services.validation_shell_service.PostValidationService", FakePostValidationService)
    try:
        validate = CloudShellExecutor().execute(db, raw_command=f"nb validate request {request.request_number}", user_context=context)
        report = CloudShellExecutor().execute(db, raw_command=f"nb remediation report {request.request_number}", user_context=context)
        destroy = CloudShellExecutor().execute(db, raw_command=f"nb terraform destroy {request.request_number}", user_context=context)

        assert validate.status == "success"
        assert "Validation Result:" in validate.output
        assert report.status == "success"
        assert "Remediation Final Report" in report.output
        assert destroy.status == "blocked"
        assert account.account_id
    finally:
        db.close()
