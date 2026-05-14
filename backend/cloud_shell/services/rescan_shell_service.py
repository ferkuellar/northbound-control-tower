from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from models.user import User
from provisioning.rescan_service import RescanService


class RescanAccountCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb rescan account <account_id>").build()
        user = db.get(User, uuid.UUID(str(user_context.user_id))) if user_context.user_id else None
        if user is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("User context not found.").build()
        service = RescanService(db)
        account = service.get_account(tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0])
        if account is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Cloud account not found: {parsed.args[0]}").build()
        result = service.rescan_account(cloud_account=account, current_user=user, trigger_source="MANUAL")
        db.commit()
        status = "success" if result.success else "error"
        builder = (
            ShellResponseBuilder(parsed.command_name)
            .with_status(status)
            .line("Rescan completed." if result.success else "Rescan failed.")
            .line("")
            .line("Account:")
            .line(account.account_id or account.name)
            .line("")
            .line("Provider:")
            .line(account.provider.upper())
            .line("")
            .line("Collector Run:")
            .line(result.collector_run.collector_run_code)
            .line("")
            .line("Resources Collected:")
            .line(str(result.collector_run.resources_collected_count))
            .line("")
            .line("Findings Generated:")
            .line(str(result.collector_run.findings_generated_count))
        )
        if result.error_message:
            builder.line("").line("Reason:").line(result.error_message)
        return (
            builder.line("")
            .line("Artifacts:")
            .line("- rescan.log")
            .line("- rescan-inventory-snapshot.json")
            .line("- collector-run-metadata.json")
            .build()
        )
