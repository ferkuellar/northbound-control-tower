from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.post_validation_service import PostValidationService
from provisioning.remediation_report_service import RemediationReportService
from provisioning.service import ProvisioningRequestService


class RemediationReportCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb remediation report <request_id>").build()
        request = ProvisioningRequestService(db).get_by_number_or_id(
            tenant_id=uuid.UUID(str(user_context.tenant_id)),
            identifier=parsed.args[0],
        )
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Provisioning request not found: {parsed.args[0]}").build()
        validation = PostValidationService(db).latest_validation(request)
        if validation is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("No post-remediation validation found for this request.").build()
        markdown = RemediationReportService(db).latest_report_markdown(request)
        if markdown:
            return ShellResponseBuilder(parsed.command_name).with_status("success").line(markdown.strip()).meta("related_request_id", request.request_number).build()
        finding = validation.before_finding_snapshot_json
        return (
            ShellResponseBuilder(parsed.command_name)
            .with_status("success")
            .line(f"Remediation Final Report - {request.request_number}")
            .line("")
            .line("Finding:")
            .line(f"{finding.get('id')} - {finding.get('title')}")
            .line("")
            .line("Request Status:")
            .line(request.status)
            .line("")
            .line("Validation Result:")
            .line(validation.result)
            .line("")
            .line("Evidence:")
            .line("- post-validation-result.md")
            .line("- remediation-final-report.md")
            .meta("related_request_id", request.request_number)
            .build()
        )
