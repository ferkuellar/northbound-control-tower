from __future__ import annotations

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from cloud_shell.services.fix_shell_service import REQUEST_STORE


class RequestsListCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        builder = ShellResponseBuilder(parsed.command_name).line("ID        Status   Template")
        if not REQUEST_STORE:
            return builder.line("No provisioning request drafts exist in this shell session.").build()
        for request in REQUEST_STORE.values():
            builder.line(f"{request['request_id']:<10}{request['status']:<9}{request['template']}")
        return builder.build()


class RequestsShowCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb requests show <request_id>").build()
        request = REQUEST_STORE.get(parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Request not found: {parsed.args[0]}").build()
        return (
            ShellResponseBuilder(parsed.command_name)
            .line(f"Request ID: {request['request_id']}")
            .line(f"Finding: {request['finding_id']}")
            .line(f"Template: {request['template']}")
            .line(f"Status: {request['status']}")
            .line("Terraform execution: Disabled in this phase")
            .build()
        )

