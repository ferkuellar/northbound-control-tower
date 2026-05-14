from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.security_scan_service import CHECKOV_NOT_FOUND, SecurityScanService
from provisioning.service import ProvisioningRequestService


class SecurityScanCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb security scan <request_id>").build()
        service = ProvisioningRequestService(db)
        request = service.get_by_number_or_id(tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Provisioning request not found: {parsed.args[0]}").build()
        try:
            result = SecurityScanService(db).scan(request, created_by_user_id=user_context.user_id)
        except ValueError as exc:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(str(exc)).build()

        summary = result.summary
        if result.reason:
            return (
                ShellResponseBuilder(parsed.command_name)
                .with_status("error")
                .line(f"Security scan failed for {request.request_number}.")
                .line("")
                .line("Reason:")
                .line("Checkov CLI not found." if result.reason == CHECKOV_NOT_FOUND else result.reason)
                .line("")
                .line("Action:")
                .line("Install Checkov in the provisioning worker image.")
                .line("")
                .line("Status:")
                .line(request.status)
                .meta("related_request_id", request.request_number)
                .meta("checkov_summary", summary)
                .build()
            )

        return (
            ShellResponseBuilder(parsed.command_name)
            .with_status("success" if request.status != "SECURITY_SCAN_BLOCKED" else "blocked")
            .line(f"Security scan completed for {request.request_number}.")
            .line("")
            .line("Checkov:")
            .line(f"Passed: {summary['passed_count']}")
            .line(f"Failed: {summary['failed_count']}")
            .line(f"Skipped: {summary['skipped_count']}")
            .line(f"Blocking: {summary['blocking_findings_count']}")
            .line("")
            .line("Status:")
            .line(request.status)
            .line("")
            .line("Artifacts:")
            .line("- checkov.json")
            .line("- checkov.log")
            .line("")
            .line("Next:")
            .line(f"nb cost estimate {request.request_number}")
            .meta("related_request_id", request.request_number)
            .meta("checkov_summary", summary)
            .build()
        )
