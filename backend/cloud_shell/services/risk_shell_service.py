from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.risk_summary_service import RiskSummaryService
from provisioning.service import ProvisioningRequestService


class RiskSummaryCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb risk summary <request_id>").build()
        service = ProvisioningRequestService(db)
        request = service.get_by_number_or_id(tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Provisioning request not found: {parsed.args[0]}").build()
        try:
            summary = RiskSummaryService(db).generate(request, created_by_user_id=user_context.user_id)
        except ValueError as exc:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(str(exc)).build()

        terraform = summary["terraform"]
        security = summary["security"]
        cost = summary["cost"]
        return (
            ShellResponseBuilder(parsed.command_name)
            .with_status("success")
            .line(f"Risk Summary for {request.request_number}")
            .line("")
            .line("Terraform:")
            .line(f"- Add: {terraform.get('add_count', 0)}")
            .line(f"- Change: {terraform.get('change_count', 0)}")
            .line(f"- Delete: {terraform.get('delete_count', 0)}")
            .line(f"- Replace: {terraform.get('replace_count', 0)}")
            .line("")
            .line("Security:")
            .line(f"- Failed Checks: {security.get('failed_count', 0)}")
            .line(f"- Blocking Findings: {security.get('blocking_findings_count', 0)}")
            .line("")
            .line("Cost:")
            .line(f"- Projected Monthly Cost: ${cost.get('total_monthly_cost') or 'Unavailable'}")
            .line(f"- Monthly Diff: {cost.get('diff_total_monthly_cost') or 'Unavailable'}")
            .line("")
            .line("Recommendation:")
            .line(summary["recommendation"])
            .line("")
            .line("Next:")
            .line(f"nb gates evaluate {request.request_number}")
            .meta("related_request_id", request.request_number)
            .meta("risk_summary", summary)
            .build()
        )
