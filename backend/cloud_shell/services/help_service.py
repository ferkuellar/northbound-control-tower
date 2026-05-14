from __future__ import annotations

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext


class HelpCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        return (
            ShellResponseBuilder(parsed.command_name)
            .line("Available commands:")
            .line("")
            .line("Diagnostics:")
            .line("  nb status")
            .line("  nb findings list")
            .line("  nb findings show <finding_id>")
            .line("")
            .line("Remediation Planning:")
            .line("  nb fix suggest <finding_id>")
            .line("  nb fix plan <finding_id>")
            .line("")
            .line("Requests:")
            .line("  nb requests list")
            .line("  nb requests show <request_id>")
            .line("")
            .line("Evidence:")
            .line("  nb evidence show <request_id>")
            .line("")
            .line("Terraform:")
            .line("  nb terraform validate <request_id>   [disabled in this phase]")
            .line("  nb terraform plan <request_id>       [disabled in this phase]")
            .line("  nb terraform apply <request_id>      [disabled in this phase]")
            .build()
        )

