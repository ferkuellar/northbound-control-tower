import uuid

from sqlalchemy.orm import Session

from cloud_shell.authorization import CloudShellAuthorizationService
from cloud_shell.command_executor import CloudShellExecutor
from cloud_shell.command_parser import CommandParser
from cloud_shell.default_registry import build_default_registry
from cloud_shell.errors import CommandAuthorizationError, CommandBlockedError, CommandParseError
from cloud_shell.schemas import ShellUserContext
from core.database import SessionLocal
from models.cloud_account import CloudAccount
from models.cloud_shell_audit import CloudShellCommandAudit
from models.finding import Finding
from models.provisioning_request import ProvisioningArtifact, ProvisioningRequest
from models.tenant import Tenant
from models.user import User, UserRole


def test_command_parser_parses_status() -> None:
    parsed = CommandParser().parse("nb status")

    assert parsed.namespace == "nb"
    assert parsed.group == "status"
    assert parsed.action is None


def test_command_parser_parses_finding_show() -> None:
    parsed = CommandParser().parse("nb findings show FIND-001")

    assert parsed.group == "findings"
    assert parsed.action == "show"
    assert parsed.args == ["FIND-001"]


def test_command_parser_rejects_bash_and_destroy() -> None:
    parser = CommandParser()

    for command in ["bash", "terraform destroy", ""]:
        try:
            parser.parse(command)
        except (CommandBlockedError, CommandParseError):
            pass
        else:
            raise AssertionError(f"Command should be rejected: {command}")


def test_command_registry_finds_valid_commands() -> None:
    registry = build_default_registry()

    status = registry.get(CommandParser().parse("nb status"))
    terraform = registry.get(CommandParser().parse("nb terraform plan REQ-1001"))
    apply = registry.get(CommandParser().parse("nb terraform apply REQ-1001"))

    assert status.enabled is True
    assert terraform.enabled is True
    assert apply.enabled is True


def test_authorization_role_mapping() -> None:
    service = CloudShellAuthorizationService()
    viewer = ShellUserContext(user_id=None, tenant_id=None, role="VIEWER")
    operator = ShellUserContext(user_id=None, tenant_id=None, role="OPERATOR")

    service.authorize(user_context=viewer, required_role="VIEWER")
    service.authorize(user_context=operator, required_role="OPERATOR")
    try:
        service.authorize(user_context=viewer, required_role="OPERATOR")
    except CommandAuthorizationError:
        pass
    else:
        raise AssertionError("VIEWER should not execute OPERATOR commands")


def _seed_shell_user(role: UserRole = UserRole.ADMIN) -> tuple[Session, User]:
    db = SessionLocal()
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"Shell Tenant {suffix}", slug=f"shell-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    user = User(
        tenant_id=tenant.id,
        email=f"shell-{role.value.lower()}-{suffix}@northbound.local",
        full_name="Shell User",
        hashed_password="not-used",
        role=role.value,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return db, user


def _seed_shell_finding(db: Session, user: User) -> Finding:
    account = CloudAccount(
        tenant_id=user.tenant_id,
        provider="aws",
        name="AWS Shell",
        auth_type="profile",
        default_region="us-east-1",
        is_active=True,
    )
    db.add(account)
    db.flush()
    finding = Finding(
        tenant_id=user.tenant_id,
        cloud_account_id=account.id,
        resource_id=None,
        provider="aws",
        finding_type="public_exposure",
        category="security",
        severity="high",
        status="open",
        title="Public SSH exposure",
        description="Security group allows public ingress.",
        evidence={"cidr": "0.0.0.0/0"},
        recommendation="Validate approved access path before making changes.",
        rule_id="public_exposure_v1",
        fingerprint=uuid.uuid4().hex,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def test_command_executor_executes_and_audits_status() -> None:
    db, user = _seed_shell_user()
    try:
        context = ShellUserContext(user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        response = CloudShellExecutor().execute(db, raw_command="nb status", user_context=context)

        assert response.status == "success"
        assert "Controlled Command Shell" in response.output
        audit = db.get(CloudShellCommandAudit, uuid.UUID(response.metadata["audit_id"]))
        assert audit is not None
        assert audit.command_name == "nb status"
        assert audit.status == "SUCCEEDED"
    finally:
        db.close()


def test_command_executor_handles_unknown_without_stack_trace() -> None:
    db, user = _seed_shell_user()
    try:
        context = ShellUserContext(user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        response = CloudShellExecutor().execute(db, raw_command="nb nope", user_context=context)

        assert response.status == "error"
        assert "Unknown Northbound command" in response.output
        assert "Traceback" not in response.output
    finally:
        db.close()


def test_viewer_cannot_fix_plan() -> None:
    db, user = _seed_shell_user(UserRole.VIEWER)
    try:
        context = ShellUserContext(user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        response = CloudShellExecutor().execute(db, raw_command="nb fix plan FIND-001", user_context=context)

        assert response.status == "rejected"
        assert "Insufficient role" in response.output
    finally:
        db.close()


def test_fix_plan_persists_provisioning_request_and_artifacts() -> None:
    db, user = _seed_shell_user(UserRole.ANALYST)
    finding = _seed_shell_finding(db, user)
    try:
        context = ShellUserContext(user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        response = CloudShellExecutor().execute(db, raw_command=f"nb fix plan {finding.id}", user_context=context)

        assert response.status == "success"
        assert "Provisioning request created" in response.output
        request = db.query(ProvisioningRequest).filter_by(finding_id=finding.id).one()
        artifacts = db.query(ProvisioningArtifact).filter_by(provisioning_request_id=request.id).all()
        assert request.status == "DRAFT"
        assert request.template_key == "cloud-public-exposure-review"
        assert request.tfvars_json["terraform_execution_enabled"] is False
        assert len(artifacts) == 3
    finally:
        db.close()


def test_requests_show_reads_persisted_request() -> None:
    db, user = _seed_shell_user(UserRole.ANALYST)
    finding = _seed_shell_finding(db, user)
    try:
        context = ShellUserContext(user_id=str(user.id), tenant_id=str(user.tenant_id), role=user.role)
        create_response = CloudShellExecutor().execute(db, raw_command=f"nb fix plan {finding.id}", user_context=context)
        request_number = str(create_response.metadata["related_request_id"])
        show_response = CloudShellExecutor().execute(db, raw_command=f"nb requests show {request_number}", user_context=context)
        evidence_response = CloudShellExecutor().execute(db, raw_command=f"nb evidence show {request_number}", user_context=context)

        assert "Generated artifacts" in show_response.output
        assert "terraform.tfvars.json" in evidence_response.output
    finally:
        db.close()
