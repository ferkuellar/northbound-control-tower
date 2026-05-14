from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from models.finding import Finding


REQUEST_STORE: dict[str, dict[str, str]] = {}


def _get_finding(db: Session, tenant_id: str | None, identifier: str) -> Finding | None:
    query = select(Finding).where(Finding.tenant_id == uuid.UUID(str(tenant_id)))
    try:
        query = query.where(Finding.id == uuid.UUID(identifier))
    except ValueError:
        query = query.where(Finding.title.ilike(f"%{identifier}%"))
    return db.scalar(query)


def _template_for(finding: Finding) -> str:
    if finding.finding_type == "public_exposure":
        return "cloud-public-exposure-review"
    if finding.finding_type == "unattached_volume":
        return "cloud-volume-snapshot-and-cleanup"
    if finding.finding_type == "missing_tags":
        return "cloud-tagging-governance"
    if finding.finding_type == "observability_gap":
        return "cloud-monitoring-baseline"
    return f"{finding.provider}-{finding.finding_type}".replace("_", "-")


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

        request_id = f"REQ-{len(REQUEST_STORE) + 1001}"
        REQUEST_STORE[request_id] = {
            "request_id": request_id,
            "finding_id": str(finding.id),
            "template": _template_for(finding),
            "status": "DRAFT",
        }

        return (
            ShellResponseBuilder(parsed.command_name)
            .line("Provisioning request created.")
            .line("")
            .line(f"Request ID: {request_id}")
            .line(f"Finding: {finding.id}")
            .line(f"Template: {REQUEST_STORE[request_id]['template']}")
            .line("Status: DRAFT")
            .line("Terraform execution: Disabled in this phase")
            .line("")
            .line("Next available command:")
            .line(f"nb requests show {request_id}")
            .meta("related_request_id", request_id)
            .build()
        )

