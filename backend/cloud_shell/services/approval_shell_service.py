from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.approval_service import ApprovalService


def _note(parsed: ParsedCommand) -> str:
    value = parsed.flags.get("note")
    return str(value).strip() if isinstance(value, str) else ""


class ApprovalsListCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        requests = ApprovalService(db).list_pending(tenant_id=uuid.UUID(str(user_context.tenant_id)))
        if not requests:
            return ShellResponseBuilder(parsed.command_name).line("No provisioning requests are currently waiting for approval.").build()

        builder = (
            ShellResponseBuilder(parsed.command_name)
            .line("Pending Approvals")
            .line("")
            .line("Request    Environment   Risk       Cost Diff   Security   Gates      Status")
        )
        for request in requests:
            evidence = request.evidence or {}
            risk = evidence.get("risk_summary") or {}
            security = evidence.get("security_scan") or risk.get("security") or {}
            cost = evidence.get("cost_estimate") or risk.get("cost") or {}
            gates = evidence.get("policy_gates") or {}
            environment = request.input_variables.get("environment") or request.tfvars_json.get("environment") or risk.get("environment") or "dev"
            security_status = "PASS" if int(security.get("blocking_findings_count") or 0) == 0 else "BLOCKED"
            gates_status = "PASS" if gates.get("blocked") is False else "BLOCKED"
            cost_diff = cost.get("diff_total_monthly_cost") or "Unavailable"
            builder.line(
                f"{request.request_number:<10} {str(environment):<12} {request.risk_level:<10} {str(cost_diff):<11} {security_status:<10} {gates_status:<10} {request.status}"
            )
        return builder.build()


class ApprovalsShowCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb approvals show <request_id>").build()
        request, approval, snapshots = ApprovalService(db).get_detail(
            tenant_id=uuid.UUID(str(user_context.tenant_id)),
            identifier=parsed.args[0],
        )
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Approval not found: {parsed.args[0]}").build()

        terraform = snapshots.get("plan_summary") or {}
        security = snapshots.get("security") or {}
        cost = snapshots.get("cost") or {}
        gates = snapshots.get("gates") or {}
        environment = approval.environment if approval else "dev"
        return (
            ShellResponseBuilder(parsed.command_name)
            .line(f"Approval Detail - {request.request_number}")
            .line("")
            .line("Request:")
            .line(f"- Template: {request.template_key}")
            .line(f"- Environment: {environment}")
            .line(f"- Provider: {request.provider}")
            .line(f"- Finding: {request.finding_id}")
            .line("")
            .line("Terraform Plan:")
            .line(f"- Add: {terraform.get('add_count', 0)}")
            .line(f"- Change: {terraform.get('change_count', 0)}")
            .line(f"- Delete: {terraform.get('delete_count', 0)}")
            .line(f"- Replace: {terraform.get('replace_count', 0)}")
            .line(f"- Destructive Changes: {'Yes' if terraform.get('has_destructive_changes') else 'No'}")
            .line("")
            .line("Security:")
            .line(f"- Failed Checks: {security.get('failed_count', 0)}")
            .line(f"- Blocking Findings: {security.get('blocking_findings_count', 0)}")
            .line("")
            .line("Cost:")
            .line(f"- Projected Monthly Cost: ${cost.get('total_monthly_cost') or 'Unavailable'}")
            .line(f"- Monthly Diff: {cost.get('diff_total_monthly_cost') or 'Unavailable'}")
            .line("")
            .line("Gates:")
            .line(f"- Decision: {gates.get('decision') or 'UNKNOWN'}")
            .line(f"- Blocked: {'Yes' if gates.get('blocked') else 'No'}")
            .line("")
            .line("Approval:")
            .line("- Required: Yes")
            .line(f"- Level: {approval.approval_level if approval else 'STANDARD'}")
            .line(f"- Status: {approval.status if approval else 'PENDING'}")
            .line("")
            .line("Available actions:")
            .line(f'nb approve {request.request_number} --note "Reviewed and approved"')
            .line(f'nb reject {request.request_number} --note "Rejected reason"')
            .meta("related_request_id", request.request_number)
            .build()
        )


class ApproveCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line('Usage: nb approve <request_id> --note "..."').build()
        note = _note(parsed)
        if not note:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Approval note is required.").build()
        try:
            result = ApprovalService(db).approve(
                tenant_id=uuid.UUID(str(user_context.tenant_id)),
                identifier=parsed.args[0],
                note=note,
                user_context=user_context,
            )
        except ValueError as exc:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(str(exc)).build()

        return (
            ShellResponseBuilder(parsed.command_name)
            .line(f"Approval recorded for {result.request.request_number}.")
            .line("")
            .line("Decision:")
            .line(result.approval.decision)
            .line("")
            .line("Approved by:")
            .line(str(result.approval.approved_by or user_context.user_id or "current_user"))
            .line("")
            .line("Note:")
            .line(note)
            .line("")
            .line("Request Status:")
            .line(result.request.status)
            .line("")
            .line("Next phase required:")
            .line("Phase F - Controlled Terraform Apply")
            .meta("related_request_id", result.request.request_number)
            .meta("approval_code", result.approval.approval_code)
            .build()
        )


class RejectCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line('Usage: nb reject <request_id> --note "..."').build()
        note = _note(parsed)
        if not note:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Rejection note is required.").build()
        try:
            result = ApprovalService(db).reject(
                tenant_id=uuid.UUID(str(user_context.tenant_id)),
                identifier=parsed.args[0],
                note=note,
                user_context=user_context,
            )
        except ValueError as exc:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(str(exc)).build()

        return (
            ShellResponseBuilder(parsed.command_name)
            .line("Request rejected.")
            .line("")
            .line("Request:")
            .line(result.request.request_number)
            .line("")
            .line("Decision:")
            .line(result.approval.decision)
            .line("")
            .line("Reason:")
            .line(note)
            .line("")
            .line("Request Status:")
            .line(result.request.status)
            .line("")
            .line("No apply can be executed for this request.")
            .meta("related_request_id", result.request.request_number)
            .meta("approval_code", result.approval.approval_code)
            .build()
        )
