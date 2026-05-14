from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext
from models.finding import Finding


class FindingShellAdapter:
    """Adapter from Finding model to terminal rows."""

    @staticmethod
    def row(finding: Finding) -> str:
        return (
            f"{str(finding.id)[:8]:<10}"
            f"{finding.severity.upper():<11}"
            f"{finding.provider.upper():<11}"
            f"{finding.category:<16}"
            f"{finding.status.upper():<9}"
            f"{finding.title}"
        )

    @staticmethod
    def detail(finding: Finding) -> list[str]:
        return [
            f"Finding: {finding.id}",
            f"Severity: {finding.severity.upper()}",
            f"Provider: {finding.provider.upper()}",
            f"Type: {finding.finding_type}",
            f"Category: {finding.category}",
            f"Status: {finding.status.upper()}",
            "",
            f"Issue: {finding.title}",
            finding.description,
            "",
            "Recommendation:",
            finding.recommendation,
        ]


class FindingsListCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        query = select(Finding).where(Finding.tenant_id == uuid.UUID(str(user_context.tenant_id))).order_by(Finding.last_seen_at.desc()).limit(10)
        severity = parsed.flags.get("severity")
        if isinstance(severity, str):
            query = query.where(Finding.severity == severity.lower())
        findings = list(db.scalars(query))

        builder = ShellResponseBuilder(parsed.command_name).line("ID        Severity   Provider   Category        Status   Issue")
        if not findings:
            return builder.line("No findings found for the current tenant.").build()
        for finding in findings:
            builder.line(FindingShellAdapter.row(finding))
        return builder.build()


class FindingsShowCommand:
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        if not parsed.args:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line("Usage: nb findings show <finding_id>").build()

        identifier = parsed.args[0]
        tenant_id = uuid.UUID(str(user_context.tenant_id))
        query = select(Finding).where(Finding.tenant_id == tenant_id)
        try:
            query = query.where(Finding.id == uuid.UUID(identifier))
        except ValueError:
            query = query.where(Finding.title.ilike(f"%{identifier}%"))

        finding = db.scalar(query)
        if finding is None:
            return ShellResponseBuilder(parsed.command_name).with_status("error").line(f"Finding not found: {identifier}").build()

        builder = ShellResponseBuilder(parsed.command_name)
        for line in FindingShellAdapter.detail(finding):
            builder.line(line)
        return builder.build()

