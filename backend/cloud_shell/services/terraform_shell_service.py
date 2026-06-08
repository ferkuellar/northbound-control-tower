from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.terraform_apply_service import TerraformApplyService
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
            .line("- workspace prepared: OK")
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


class TerraformApplyCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb terraform apply <request_id>").build()
        service = ProvisioningRequestService(db)
        request = service.get_by_number_or_id(tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Provisioning request not found: {parsed.args[0]}").build()

        result = TerraformApplyService(db).apply(request, created_by_user_id=user_context.user_id)
        if not result.precheck.passed:
            reason = result.precheck.reasons[0] if result.precheck.reasons else "Apply pre-check failed."
            return (
                ShellResponseBuilder(parsed.command_name)
                .with_status("blocked")
                .line(f"Apply blocked for {request.request_number}.")
                .line("")
                .line("Reason:")
                .line(reason)
                .line("")
                .line("Current status:")
                .line(request.status)
                .line("")
                .line("No infrastructure changes were executed.")
                .meta("related_request_id", request.request_number)
                .meta("precheck", result.precheck.payload())
                .build()
            )

        if not result.success:
            return (
                ShellResponseBuilder(parsed.command_name)
                .with_status("error")
                .line(f"Terraform apply failed for {request.request_number}.")
                .line("")
                .line("Exit code:")
                .line(str(result.exit_code))
                .line("")
                .line("Status:")
                .line(request.status)
                .line("")
                .line("Evidence:")
                .line("- apply.log")
                .line("- apply-metadata.json")
                .line("")
                .line("No post-validation was executed.")
                .meta("related_request_id", request.request_number)
                .build()
            )

        return (
            ShellResponseBuilder(parsed.command_name)
            .with_status("success")
            .line(f"Controlled Terraform apply started for {request.request_number}.")
            .line("")
            .line("Pre-checks:")
            .line("- Request approved: OK")
            .line("- Approval valid: OK")
            .line("- Plan artifact exists: OK")
            .line("- Plan checksum verified: OK")
            .line("- Gates verified: OK")
            .line("- Destructive changes: none")
            .line("- Execution lock acquired: OK")
            .line("")
            .line("Running:")
            .line("terraform apply -input=false -no-color plan.out")
            .line("")
            .line("Apply completed successfully.")
            .line("")
            .line("Status:")
            .line(request.status)
            .line("")
            .line("Artifacts:")
            .line("- apply.log")
            .line("- apply-metadata.json")
            .line("- outputs.json")
            .line("")
            .line("Next:")
            .line(f"nb outputs show {request.request_number}")
            .line("")
            .line("Upcoming phase:")
            .line("Phase G - Post-Remediation Validation")
            .meta("related_request_id", request.request_number)
            .build()
        )


TerraformApplyDisabledCommand = TerraformApplyCommand


class TerraformDestroyBlockedCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        return (
            ShellResponseBuilder(parsed.command_name)
            .with_status("blocked")
            .line("Command blocked. Terraform destroy is not available from Northbound Cloud Shell.")
            .build()
        )
