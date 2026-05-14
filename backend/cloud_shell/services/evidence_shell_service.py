from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from provisioning.service import ProvisioningRequestService


class EvidenceShowCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb evidence show <request_id>").build()
        service = ProvisioningRequestService(db)
        request = service.get_by_number_or_id(tenant_id=uuid.UUID(str(user_context.tenant_id)), identifier=parsed.args[0])
        if request is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Evidence not found: {parsed.args[0]}").build()
        artifacts = service.list_artifacts(request=request)
        builder = (
            ShellResponseBuilder(parsed.command_name)
            .line(f"Evidence for {request.request_number}")
            .line("")
            .line(f"Status: {request.status}")
            .line(f"Approval required: {request.approval_required}")
            .line("")
            .line("Stored artifacts:")
            .meta("related_request_id", request.request_number)
        )
        for artifact in artifacts:
            size = f"{artifact.size_bytes} bytes" if artifact.size_bytes is not None else "metadata"
            builder.line(f"{artifact.artifact_type}")
            builder.line(f"- {artifact.name}")
            builder.line(f"- created_at: {artifact.created_at.isoformat() if artifact.created_at else artifact.generated_at.isoformat()}")
            builder.line(f"- size: {size}")
            if artifact.storage_path:
                builder.line(f"- path: {artifact.storage_path}")
            builder.line("")
        return builder.build()
