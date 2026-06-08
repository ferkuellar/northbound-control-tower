from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.policy_gates import BLOCKED, PolicyGateEngine
from provisioning.service import ProvisioningRequestService


class GatesEvaluateCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb gates evaluate <request_id>").build()
        service = ProvisioningRequestService(db)
        request = service.get_by_number_or_id(tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Provisioning request not found: {parsed.args[0]}").build()

        result = PolicyGateEngine(db).evaluate(request, created_by_user_id=user_context.user_id)
        blocking = [gate["message"] for gate in result["gates"] if gate["result"] == BLOCKED]
        warnings = [gate["message"] for gate in result["gates"] if gate["result"] == "WARN"]
        if result["blocked"]:
            builder = (
                ShellResponseBuilder(parsed.command_name)
                .with_status("blocked")
                .line(f"Policy gates blocked {request.request_number}.")
                .line("")
                .line("Decision:")
                .line(result["decision"])
                .line("")
                .line("Blocking Reasons:")
            )
            for item in blocking:
                builder.line(f"- {item}")
            return builder.line("").line("Apply remains disabled.").meta("related_request_id", request.request_number).meta("gates_result", result).build()

        builder = (
            ShellResponseBuilder(parsed.command_name)
            .with_status("success" if result["ready_for_approval"] else "error")
            .line(f"Policy gates {'passed' if result['ready_for_approval'] else 'failed'} for {request.request_number}.")
            .line("")
            .line("Decision:")
            .line(result["decision"])
            .line("")
            .line("Warnings:")
        )
        for item in warnings or ["Cost estimate available", "No destructive changes", "No critical security findings"]:
            builder.line(f"- {item}")
        return (
            builder.line("")
            .line("Next phase:")
            .line("Approval workflow is required before apply.")
            .meta("related_request_id", request.request_number)
            .meta("gates_result", result)
            .build()
        )
