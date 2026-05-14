from __future__ import annotations

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.template_catalog import TEMPLATE_CATALOG, get_template


class TemplatesListCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        builder = ShellResponseBuilder(parsed.command_name).line("ID                            Provider   Terraform   Risk      Description")
        for template in sorted(TEMPLATE_CATALOG.values(), key=lambda item: item.key):
            terraform = "enabled" if template.terraform_enabled else "disabled"
            builder.line(f"{template.key:<30}{template.provider:<11}{terraform:<12}{template.risk_level:<10}{template.title}")
        return builder.build()


class TemplatesShowCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb templates show <template_id>").build()
        template = get_template(parsed.args[0])
        if template is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Template not found: {parsed.args[0]}").build()
        return (
            ShellResponseBuilder(parsed.command_name)
            .line(f"Template: {template.key}")
            .line(f"Title: {template.title}")
            .line(f"Provider: {template.provider}")
            .line(f"Risk: {template.risk_level}")
            .line(f"Terraform enabled: {template.terraform_enabled}")
            .line(f"Approval required: {template.requires_approval}")
            .line(f"Module path: {template.module_path}")
            .line("")
            .line(template.description)
            .build()
        )
