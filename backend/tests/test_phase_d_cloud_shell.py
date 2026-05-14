from cloud_shell.command_parser import CommandParser
from cloud_shell.errors import CommandBlockedError
from cloud_shell.schemas import ParsedCommand, ShellUserContext
from cloud_shell.services.terraform_shell_service import TerraformApplyDisabledCommand


def test_phase_d_commands_parse() -> None:
    parser = CommandParser()

    assert parser.parse("nb security scan REQ-1001").group == "security"
    assert parser.parse("nb cost estimate REQ-1001").group == "cost"
    assert parser.parse("nb risk summary REQ-1001").group == "risk"
    assert parser.parse("nb gates evaluate REQ-1001").group == "gates"


def test_terraform_apply_requires_request_id() -> None:
    response = TerraformApplyDisabledCommand().execute(
        None,
        ParsedCommand(namespace="nb", group="terraform", action="apply", args=[]),
        ShellUserContext(user_id=None, tenant_id=None, role="ADMIN"),
    )

    assert response.status == "error"
    assert "Usage: nb terraform apply <request_id>" in response.output


def test_terraform_destroy_remains_blocked() -> None:
    parser = CommandParser()

    try:
        parser.parse("nb terraform destroy REQ-1001")
    except CommandBlockedError as exc:
        assert "Terraform destroy is not available" in str(exc)
    else:
        raise AssertionError("terraform destroy must be blocked")
