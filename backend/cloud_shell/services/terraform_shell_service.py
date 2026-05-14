from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.terraform_runner import TERRAFORM_NOT_FOUND, TerraformRunner
from provisioning.service import ProvisioningRequestService


class TerraformValidateCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb terraform validate <request_id>").build()
        service = ProvisioningRequestService(db)
        request = service.get_by_number_or_id(tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Provisioning request not found: {parsed.args[0]}").build()

        results = TerraformRunner(db).validate(request, created_by_user_id=user_context.user_id)
        init_result = results["init"]
        validate_result = results.get("validate")
        builder = (
            ShellResponseBuilder(parsed.command_name)
            .with_status("success" if validate_result and validate_result.success else "error")
            .line(f"Terraform validation {'completed' if validate_result and validate_result.success else 'failed'} for {request.request_number}.")
            .line("")
            .line("Workspace:")
            .line(request.workspace_path or "not prepared")
            .line("")
            .line("Steps:")
            .line(f"- workspace prepared: OK")
            .line(f"- terraform init: {'OK' if init_result.success else 'FAILED'}")
        )
        if validate_result:
            builder.line(f"- terraform validate: {'OK' if validate_result.success else 'FAILED'}")
        if init_result.stderr == TERRAFORM_NOT_FOUND or (validate_result and validate_result.stderr == TERRAFORM_NOT_FOUND):
            builder.line("").line(TERRAFORM_NOT_FOUND)
        builder.line("").line("Status:").line(request.status).line("").line("Artifacts:")
        builder.line("- init.log")
        if validate_result:
            builder.line("- validate.log")
        builder.line("- execution-metadata.json")
        if validate_result and validate_result.success:
            builder.line("").line("Next:").line(f"nb terraform plan {request.request_number}")
        else:
            builder.line("").line("Run:").line(f"nb evidence show {request.request_number}")
        return builder.meta("related_request_id", request.request_number).build()


class TerraformPlanCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb terraform plan <request_id>").build()
        service = ProvisioningRequestService(db)
        request = service.get_by_number_or_id(tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Provisioning request not found: {parsed.args[0]}").build()
        try:
            results = TerraformRunner(db).plan(request, created_by_user_id=user_context.user_id)
        except ValueError as exc:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(str(exc)).build()

        plan_result = results["plan"]
        show_result = results.get("show")
        summary = show_result.plan_summary if show_result else None
        builder = (
            ShellResponseBuilder(parsed.command_name)
            .with_status("success" if show_result and show_result.success else "error")
            .line(f"Terraform plan {'completed' if show_result and show_result.success else 'failed'} for {request.request_number}.")
            .line("")
            .line("Status:")
            .line(request.status)
            .line("")
        )
        if summary:
            builder.line("Changes:")
            builder.line(
                f"{summary['add_count']} to add, {summary['change_count']} to change, "
                f"{summary['delete_count']} to destroy, {summary['replace_count']} to replace"
            )
            if summary["has_destructive_changes"]:
                builder.line("").line("WARNING:").line("Terraform plan includes delete or replace actions.")
        elif plan_result.stderr == TERRAFORM_NOT_FOUND:
            builder.line(TERRAFORM_NOT_FOUND).line("")
        builder.line("Artifacts:").line("- plan.out").line("- plan.json").line("- plan.log")
        builder.line("").line("Next phase required before apply:").line("- security scan").line("- cost estimation").line("- approval workflow")
        return builder.meta("related_request_id", request.request_number).meta("plan_summary", summary or {}).build()


class TerraformApplyDisabledCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        return (
            ShellResponseBuilder(parsed.command_name)
            .with_status("not_implemented")
            .line("Command recognized but disabled in this phase.")
            .line("Reason: Terraform apply requires approval workflow, security gates, cost review and controlled execution policy.")
            .build()
        )
