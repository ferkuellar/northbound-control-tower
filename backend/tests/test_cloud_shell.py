import uuid

from sqlalchemy.orm import Session

from cloud_shell.authorization import CloudShellAuthorizationService
from cloud_shell.command_executor import CloudShellExecutor
from cloud_shell.command_parser import CommandParser
from cloud_shell.default_registry import build_default_registry
from cloud_shell.errors import CommandAuthorizationError, CommandBlockedError, CommandParseError
from cloud_shell.schemas import ShellUserContext
from core.database import SessionLocal
from models.cloud_shell_audit import CloudShellCommandAudit
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


def test_command_registry_finds_valid_and_marks_disabled() -> None:
    registry = build_default_registry()

    status = registry.get(CommandParser().parse("nb status"))
    terraform = registry.get(CommandParser().parse("nb terraform plan REQ-1001"))

    assert status.enabled is True
    assert terraform.enabled is False


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
