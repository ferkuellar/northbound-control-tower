from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from cloud_shell.command_registry import CommandDefinition
from cloud_shell.enums import CloudShellAuditStatus, CloudShellRiskLevel
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from models.cloud_shell_audit import CloudShellCommandAudit


class CloudShellAuditLogger:
    """Persists command evidence without storing secrets or stack traces."""

    def start(
        self,
        db: Session,
        *,
        raw_command: str,
        parsed: ParsedCommand | None,
        user_context: ShellUserContext,
        definition: CommandDefinition | None = None,
    ) -> CloudShellCommandAudit:
        audit = CloudShellCommandAudit(
            user_id=uuid.UUID(str(user_context.user_id)) if user_context.user_id else None,
            tenant_id=uuid.UUID(str(user_context.tenant_id)) if user_context.tenant_id else None,
            command_raw=raw_command[:1000],
            command_name=parsed.command_name if parsed else None,
            arguments_json={"args": parsed.args, "flags": parsed.flags} if parsed else {},
            status=CloudShellAuditStatus.RECEIVED.value,
            risk_level=(definition.risk_level.value if definition else CloudShellRiskLevel.LOW.value),
            approval_required=definition.approval_required if definition else False,
            source_ip=user_context.source_ip,
            user_agent=user_context.user_agent,
        )
        db.add(audit)
        db.flush()
        return audit

    def finish(
        self,
        db: Session,
        *,
        audit: CloudShellCommandAudit,
        status: CloudShellAuditStatus,
        response: ShellResponse | None = None,
        error_message: str | None = None,
    ) -> CloudShellCommandAudit:
        finished_at = datetime.now(UTC)
        audit.status = status.value
        audit.finished_at = finished_at
        audit.duration_ms = int((finished_at - audit.started_at).total_seconds() * 1000)
        audit.error_message = error_message
        if response is not None:
            audit.stdout = response.output[:10000]
            audit.related_request_id = response.metadata.get("related_request_id")
            audit.related_finding_id = response.metadata.get("related_finding_id")
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit
