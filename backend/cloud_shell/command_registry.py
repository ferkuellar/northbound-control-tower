from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.orm import Session

from cloud_shell.enums import CloudShellRiskLevel
from cloud_shell.errors import CommandNotFoundError
from cloud_shell.schemas import ParsedCommand, ShellResponse, ShellUserContext


class CommandHandler(Protocol):
    def execute(self, db: Session, parsed: ParsedCommand, user_context: ShellUserContext) -> ShellResponse:
        ...


@dataclass(frozen=True)
class CommandDefinition:
    namespace: str
    group: str
    action: str | None
    description: str
    required_role: str
    risk_level: CloudShellRiskLevel
    approval_required: bool
    enabled: bool
    handler: CommandHandler

    @property
    def key(self) -> tuple[str, str, str | None]:
        return (self.namespace, self.group, self.action)

    @property
    def name(self) -> str:
        parts = [self.namespace, self.group]
        if self.action:
            parts.append(self.action)
        return " ".join(parts)


class CommandRegistry:
    """Singleton command registry and allowlist."""

    _instance: "CommandRegistry | None" = None

    def __new__(cls) -> "CommandRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._commands = {}
        return cls._instance

    def register(self, definition: CommandDefinition) -> None:
        self._commands[definition.key] = definition

    def get(self, parsed: ParsedCommand) -> CommandDefinition:
        key = (parsed.namespace, parsed.group, parsed.action)
        definition = self._commands.get(key)
        if definition is None:
            raise CommandNotFoundError("Unknown Northbound command. Type: nb help")
        return definition

    def list(self) -> list[CommandDefinition]:
        return list(self._commands.values())

    def clear(self) -> None:
        self._commands.clear()

