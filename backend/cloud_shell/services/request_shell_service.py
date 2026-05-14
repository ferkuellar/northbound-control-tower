from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.service import ProvisioningRequestService


class RequestsListCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        builder = ShellResponseBuilder(parsed.command_name).line("ID        Status              Risk      Template")
        requests = ProvisioningRequestService(db).list_requests(tenant_id=uuid.UUID(str(user_context.tenant_id)))
        if not requests:
            return builder.line("No provisioning request drafts exist for the current tenant.").build()
        for request in requests:
            builder.line(f"{request.request_number:<10}{request.status:<20}{request.risk_level:<10}{request.template_key}")
        return builder.build()


class RequestsShowCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb requests show <request_id>").build()
        request = ProvisioningRequestService(db).get_by_number_or_id(
            tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0]
        )
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Request not found: {parsed.args[0]}").build()
        return (
            ShellResponseBuilder(parsed.command_name)
            .line(f"Request ID: {request.request_number}")
            .line(f"Finding: {request.finding_id}")
            .line(f"Template: {request.template_key}")
            .line(f"Status: {request.status}")
            .line(f"Risk: {request.risk_level}")
            .line(f"Approval required: {request.approval_required}")
            .line("")
            .line("Generated artifacts:")
            .line("- request-input.json")
            .line("- terraform.tfvars.json")
            .line("- phase-b-evidence.json")
            .line("Terraform execution: Disabled in this phase")
            .meta("related_request_id", request.request_number)
            .build()
        )
