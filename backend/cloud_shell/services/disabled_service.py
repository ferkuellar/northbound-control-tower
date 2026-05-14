from __future__ import annotations

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext


class DisabledFutureCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        return (
            ShellResponseBuilder(parsed.command_name)
            .with_status("not_implemented")
            .line("Command recognized but not enabled in this phase.")
            .line("Reason: Terraform execution requires provisioning workflow, approval model, security gates and evidence store.")
            .build()
        )

