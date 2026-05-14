from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.post_validation_service import PostValidationService


class ValidateRequestCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb validate request <request_id>").build()
        result = PostValidationService(db).validate_request(
            tenant_id=uuid.UUID(str(user_context.tenant_id)),
            identifier=parsed.args[0],
            user_context_user_id=user_context.user_id,
        )
        return _render_validation_response(parsed.command_name, result)


class ValidateFindingCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb validate finding <finding_id>").build()
        result = PostValidationService(db).validate_finding(
            tenant_id=uuid.UUID(str(user_context.tenant_id)),
            identifier=parsed.args[0],
            user_context_user_id=user_context.user_id,
        )
        return _render_validation_response(parsed.command_name, result)


def _render_validation_response(command_name: str, result) -> ShellResponse:
    if result.request is None or result.validation is None:
        return ShellResponseBuilder(command_name).with_status("error").line(result.error_message or "Validation failed").build()
    if result.result == "VALIDATION_FAILED":
        return (
            ShellResponseBuilder(command_name)
            .with_status("error")
            .line(f"Post-remediation validation failed for {result.request.request_number}.")
            .line("")
            .line("Reason:")
            .line(result.error_message or "Validation failed")
            .line("")
            .line("Result:")
            .line("VALIDATION_FAILED")
            .line("")
            .line("No finding status was marked RESOLVED.")
            .line("")
            .line("Artifacts:")
            .line("- rescan.log")
            .line("- collector-run-metadata.json")
            .line("- post-validation-result.json")
            .meta("related_request_id", result.request.request_number)
            .build()
        )
    builder = (
        ShellResponseBuilder(command_name)
        .with_status("success")
        .line(f"Post-remediation validation completed for {result.request.request_number}.")
        .line("")
        .line("Request:")
        .line(result.request.request_number)
        .line("")
        .line("Finding:")
        .line(str(result.validation.finding_id))
        .line("")
        .line("Validation Result:")
        .line(result.result)
        .line("")
        .line("Checks:")
    )
    for check in result.checks:
        builder.line(f"- {check['name']}: {check['status']}")
    builder.line("").line("Artifacts:")
    for artifact in result.artifacts:
        builder.line(f"- {artifact}")
    builder.line("").line("Next:").line(f"nb remediation report {result.request.request_number}")
    return builder.meta("related_request_id", result.request.request_number).build()
