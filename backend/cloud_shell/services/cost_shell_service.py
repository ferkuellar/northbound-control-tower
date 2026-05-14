from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.cost_estimation_service import CostEstimationService, INFRACOST_API_KEY_MISSING, INFRACOST_NOT_FOUND
from provisioning.service import ProvisioningRequestService


class CostEstimateCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb cost estimate <request_id>").build()
        service = ProvisioningRequestService(db)
        request = service.get_by_number_or_id(tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Provisioning request not found: {parsed.args[0]}").build()
        try:
            result = CostEstimationService(db).estimate(request, created_by_user_id=user_context.user_id)
        except ValueError as exc:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(str(exc)).build()

        summary = result.summary
        if result.reason:
            action = "Configure INFRACOST_API_KEY." if result.reason == INFRACOST_API_KEY_MISSING else "Install Infracost in the provisioning worker image."
            reason = "Infracost CLI not found." if result.reason == INFRACOST_NOT_FOUND else result.reason
            return (
                ShellResponseBuilder(parsed.command_name)
                .with_status("warning")
                .line("Cost estimate unavailable.")
                .line("")
                .line("Reason:")
                .line(reason)
                .line("")
                .line("Action:")
                .line(action)
                .line("")
                .line("Status:")
                .line(request.status)
                .meta("related_request_id", request.request_number)
                .meta("cost_summary", summary)
                .build()
            )

        return (
            ShellResponseBuilder(parsed.command_name)
            .with_status("success")
            .line(f"Cost estimate completed for {request.request_number}.")
            .line("")
            .line(f"Currency: {summary.get('currency', 'USD')}")
            .line(f"Projected Monthly Cost: ${summary.get('total_monthly_cost') or 'Unavailable'}")
            .line(f"Monthly Diff: {summary.get('diff_total_monthly_cost') or 'Unavailable'}")
            .line("")
            .line("Status:")
            .line(request.status)
            .line("")
            .line("Artifacts:")
            .line("- infracost.json")
            .line("- infracost.log")
            .line("")
            .line("Next:")
            .line(f"nb risk summary {request.request_number}")
            .meta("related_request_id", request.request_number)
            .meta("cost_summary", summary)
            .build()
        )
