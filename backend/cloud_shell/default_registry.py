from __future__ import annotations

from cloud_shell.command_registry import CommandDefinition, CommandRegistry
from cloud_shell.enums import CloudShellRiskLevel
from cloud_shell.services.disabled_service import DisabledFutureCommand
from cloud_shell.services.evidence_shell_service import EvidenceShowCommand
from cloud_shell.services.findings_shell_service import FindingsListCommand, FindingsShowCommand
from cloud_shell.services.fix_shell_service import FixPlanCommand, FixSuggestCommand
from cloud_shell.services.help_service import HelpCommand
from cloud_shell.services.request_shell_service import RequestsListCommand, RequestsShowCommand
from cloud_shell.services.status_service import StatusCommand
from cloud_shell.services.templates_shell_service import TemplatesListCommand, TemplatesShowCommand
from cloud_shell.services.terraform_shell_service import TerraformApplyDisabledCommand, TerraformPlanCommand, TerraformValidateCommand


def build_default_registry() -> CommandRegistry:
    registry = CommandRegistry()
    if registry.list():
        return registry

    definitions = [
        CommandDefinition("nb", "help", None, "Show command help", "VIEWER", CloudShellRiskLevel.LOW, False, True, HelpCommand()),
        CommandDefinition("nb", "status", None, "Show shell status", "VIEWER", CloudShellRiskLevel.LOW, False, True, StatusCommand()),
        CommandDefinition(
            "nb",
            "findings",
            "list",
            "List current tenant findings",
            "VIEWER",
            CloudShellRiskLevel.LOW,
            False,
            True,
            FindingsListCommand(),
        ),
        CommandDefinition(
            "nb",
            "findings",
            "show",
            "Show finding details",
            "VIEWER",
            CloudShellRiskLevel.LOW,
            False,
            True,
            FindingsShowCommand(),
        ),
        CommandDefinition(
            "nb",
            "fix",
            "suggest",
            "Suggest safe remediation approach",
            "OPERATOR",
            CloudShellRiskLevel.MEDIUM,
            False,
            True,
            FixSuggestCommand(),
        ),
        CommandDefinition(
            "nb",
            "fix",
            "plan",
            "Create draft provisioning request",
            "OPERATOR",
            CloudShellRiskLevel.MEDIUM,
            False,
            True,
            FixPlanCommand(),
        ),
        CommandDefinition(
            "nb",
            "templates",
            "list",
            "List provisioning templates",
            "OPERATOR",
            CloudShellRiskLevel.LOW,
            False,
            True,
            TemplatesListCommand(),
        ),
        CommandDefinition(
            "nb",
            "templates",
            "show",
            "Show provisioning template details",
            "OPERATOR",
            CloudShellRiskLevel.LOW,
            False,
            True,
            TemplatesShowCommand(),
        ),
        CommandDefinition(
            "nb",
            "requests",
            "list",
            "List draft provisioning requests",
            "OPERATOR",
            CloudShellRiskLevel.LOW,
            False,
            True,
            RequestsListCommand(),
        ),
        CommandDefinition(
            "nb",
            "requests",
            "show",
            "Show draft provisioning request",
            "OPERATOR",
            CloudShellRiskLevel.LOW,
            False,
            True,
            RequestsShowCommand(),
        ),
        CommandDefinition(
            "nb",
            "evidence",
            "show",
            "Show request evidence",
            "VIEWER",
            CloudShellRiskLevel.LOW,
            False,
            True,
            EvidenceShowCommand(),
        ),
        CommandDefinition(
            "nb",
            "terraform",
            "validate",
            "Run Terraform init and validate for a provisioning request",
            "OPERATOR",
            CloudShellRiskLevel.HIGH,
            False,
            True,
            TerraformValidateCommand(),
        ),
        CommandDefinition(
            "nb",
            "terraform",
            "plan",
            "Run Terraform plan for a validated provisioning request",
            "OPERATOR",
            CloudShellRiskLevel.HIGH,
            False,
            True,
            TerraformPlanCommand(),
        ),
        CommandDefinition(
            "nb",
            "terraform",
            "apply",
            "Future controlled Terraform apply",
            "OPERATOR",
            CloudShellRiskLevel.CRITICAL,
            True,
            False,
            TerraformApplyDisabledCommand(),
        ),
        CommandDefinition(
            "nb",
            "approve",
            None,
            "Future approval command",
            "APPROVER",
            CloudShellRiskLevel.HIGH,
            True,
            False,
            DisabledFutureCommand(),
        ),
        CommandDefinition(
            "nb",
            "validate",
            None,
            "Future post-remediation validation",
            "OPERATOR",
            CloudShellRiskLevel.MEDIUM,
            False,
            False,
            DisabledFutureCommand(),
        ),
    ]
    for definition in definitions:
        registry.register(definition)
    return registry
