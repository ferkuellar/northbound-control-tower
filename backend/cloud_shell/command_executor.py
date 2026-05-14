from __future__ import annotations

from time import perf_counter

from sqlalchemy.orm import Session

from cloud_shell.audit_logger import CloudShellAuditLogger
from cloud_shell.authorization import CloudShellAuthorizationService
from cloud_shell.command_parser import CommandParser
from cloud_shell.command_registry import CommandRegistry
from cloud_shell.default_registry import build_default_registry
from cloud_shell.enums import CloudShellAuditStatus
from cloud_shell.errors import CommandAuthorizationError, CommandBlockedError, CommandNotFoundError, CommandParseError
from cloud_shell.responses import ShellResponseBuilder
from cloud_shell.schemas import ShellResponse, ShellUserContext


class CloudShellExecutor:
    """Facade for controlled command execution."""

    def __init__(
        self,
        *,
        parser: CommandParser | None = None,
        registry: CommandRegistry | None = None,
        authorization: CloudShellAuthorizationService | None = None,
        audit_logger: CloudShellAuditLogger | None = None,
    ) -> None:
        self.parser = parser or CommandParser()
        self.registry = registry or build_default_registry()
        self.authorization = authorization or CloudShellAuthorizationService()
        self.audit_logger = audit_logger or CloudShellAuditLogger()

    def execute(self, db: Session, *, raw_command: str, user_context: ShellUserContext) -> ShellResponse:
        started = perf_counter()
        audit = None
        parsed = None
        definition = None
        try:
            audit = self.audit_logger.start(db, raw_command=raw_command, parsed=None, user_context=user_context)
            parsed = self.parser.parse(raw_command)
            definition = self.registry.get(parsed)
            audit.command_name = parsed.command_name
            audit.arguments_json = {"args": parsed.args, "flags": parsed.flags}
            audit.risk_level = definition.risk_level.value
            audit.approval_required = definition.approval_required
            db.flush()
            self.authorization.authorize(user_context=user_context, required_role=definition.required_role)

            if not definition.enabled:
                response = definition.handler.execute(db, parsed, user_context)
                response.metadata["execution_time_ms"] = int((perf_counter() - started) * 1000)
                response.metadata["audit_id"] = str(audit.id)
                self.audit_logger.finish(db, audit=audit, status=CloudShellAuditStatus.NOT_IMPLEMENTED, response=response)
                return response

            response = definition.handler.execute(db, parsed, user_context)
            response.metadata["execution_time_ms"] = int((perf_counter() - started) * 1000)
            response.metadata["audit_id"] = str(audit.id)
            status = CloudShellAuditStatus.SUCCEEDED if response.status == "success" else CloudShellAuditStatus.FAILED
            self.audit_logger.finish(db, audit=audit, status=status, response=response)
            return response
        except CommandBlockedError as exc:
            response = ShellResponseBuilder(raw_command).with_status("blocked").line(str(exc)).build()
            self._finish_error(db, audit, CloudShellAuditStatus.BLOCKED, response, str(exc))
            return response
        except (CommandParseError, CommandNotFoundError) as exc:
            response = ShellResponseBuilder(raw_command).with_status("error").line(str(exc)).build()
            self._finish_error(db, audit, CloudShellAuditStatus.REJECTED, response, str(exc))
            return response
        except CommandAuthorizationError as exc:
            response = ShellResponseBuilder(raw_command).with_status("rejected").line(str(exc)).build()
            self._finish_error(db, audit, CloudShellAuditStatus.REJECTED, response, str(exc))
            return response
        except Exception:
            response = ShellResponseBuilder(raw_command).with_status("error").line("Command failed safely. No stack trace is exposed.").build()
            self._finish_error(db, audit, CloudShellAuditStatus.FAILED, response, "Command failed safely")
            return response

    def _finish_error(
        self,
        db: Session,
        audit,
        status: CloudShellAuditStatus,
        response: ShellResponse,
        error_message: str,
    ) -> None:
        if audit is not None:
            self.audit_logger.finish(db, audit=audit, status=status, response=response, error_message=error_message)
