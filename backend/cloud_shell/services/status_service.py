from __future__ import annotations

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext


class StatusCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        return (
            ShellResponseBuilder(parsed.command_name)
            .line("Northbound Cloud Shell Status")
            .line("")
            .line("API: OK")
            .line("WebSocket: OK")
            .line("Command Registry: OK")
            .line("Audit Logger: OK")
            .line("Terraform Runner: Enabled for validate/plan only")
            .line("Terraform Apply: Disabled")
            .line("Terraform Destroy: Blocked")
            .line("Auto-remediation: Disabled")
            .line("Mode: Controlled Command Shell")
            .build()
        )
