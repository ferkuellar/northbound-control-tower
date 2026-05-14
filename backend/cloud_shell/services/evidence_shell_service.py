from __future__ import annotations

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from cloud_shell.services.fix_shell_service import REQUEST_STORE


class EvidenceShowCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb evidence show <request_id>").build()
        request = REQUEST_STORE.get(parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Evidence not found: {parsed.args[0]}").build()
        return (
            ShellResponseBuilder(parsed.command_name)
            .line(f"Evidence for {request['request_id']}")
            .line("")
            .line("Status: DRAFT")
            .line("Terraform plan artifact: Not generated in this phase")
            .line("Approval record: Not required in this phase")
            .line("Post-remediation validation: Not available in this phase")
            .build()
        )

