from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.approval_snapshots import artifact_by_type
from provisioning.enums import ProvisioningArtifactType
from provisioning.output_service import TerraformOutputService
from provisioning.service import ProvisioningRequestService


class OutputsShowCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb outputs show <request_id>").build()
        request = ProvisioningRequestService(db).get_by_number_or_id(
            tenant_id=uuid.UUID(str(user_context.tenant_id)),
            identifier=parsed.args[0],
        )
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Provisioning request not found: {parsed.args[0]}").build()
        artifact = artifact_by_type(db, request, ProvisioningArtifactType.TERRAFORM_OUTPUT_JSON)
        if artifact is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Terraform outputs not found for {request.request_number}.").build()

        rows = TerraformOutputService(db).safe_rows(artifact.content_json or {})
        builder = (
            ShellResponseBuilder(parsed.command_name)
            .line(f"Terraform Outputs - {request.request_number}")
            .line("")
            .line("output_name          sensitive   value")
        )
        sensitive_names: list[str] = []
        for name, sensitive, value in rows:
            builder.line(f"{name:<20} {sensitive:<11} {value}")
            if sensitive == "true":
                sensitive_names.append(name)
        if sensitive_names:
            builder.line("").line("Sensitive outputs:")
            for name in sensitive_names:
                builder.line(f"- {name}: [SENSITIVE]")
        return builder.meta("related_request_id", request.request_number).build()
