from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from models.finding import Finding
from models.user import User
from provisioning.service import ProvisioningRequestService
from provisioning.template_catalog import template_for_finding_type


def _get_finding(db: Session, tenant_id: str | None, identifier: str) -> Finding | None:
    query = select(Finding).where(Finding.tenant_id == uuid.UUID(str(tenant_id)))
    try:
        query = query.where(Finding.id == uuid.UUID(identifier))
    except ValueError:
        query = query.where(Finding.title.ilike(f"%{identifier}%"))
    return db.scalar(query)


def _template_for(finding: Finding) -> str:
    return template_for_finding_type(finding.finding_type, finding.provider).key


class FixSuggestCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb fix suggest <finding_id>").build()

        finding = _get_finding(db, user_context.tenant_id, parsed.args[0])
        if finding is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Finding not found: {parsed.args[0]}").build()

        template = _template_for(finding)
        return (
            ShellResponseBuilder(parsed.command_name)
            .line(f"Finding: {finding.id}")
            .line(f"Issue: {finding.title}")
            .line("")
            .line("Recommended remediation:")
            .line(f"- Review affected {finding.provider.upper()} resource evidence")
            .line("- Validate business ownership and operational impact")
            .line("- Prepare Terraform-backed change only after approval")
            .line("- Validate result after collector rescan")
            .line("")
            .line("Available template:")
            .line(template)
            .line("")
            .line("Next step:")
            .line(f"nb fix plan {finding.id}")
            .build()
        )


class FixPlanCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb fix plan <finding_id>").build()

        finding = _get_finding(db, user_context.tenant_id, parsed.args[0])
        if finding is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Finding not found: {parsed.args[0]}").build()

        current_user = db.get(User, uuid.UUID(str(user_context.user_id))) if user_context.user_id else None
        request = ProvisioningRequestService(db).create_from_finding(finding=finding, current_user=current_user)

        return (
            ShellResponseBuilder(parsed.command_name)
            .line("Provisioning request created.")
            .line("")
            .line(f"Request ID: {request.request_number}")
            .line(f"Finding: {finding.id}")
            .line(f"Template: {request.template_key}")
            .line(f"Status: {request.status}")
            .line("Terraform execution: Disabled in this phase")
            .line("Artifacts: request-input.json, terraform.tfvars.json, phase-b-evidence.json")
            .line("")
            .line("Next available command:")
            .line(f"nb requests show {request.request_number}")
            .meta("related_request_id", request.request_number)
            .meta("related_finding_id", str(finding.id))
            .build()
        )
