from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class ParsedCommand:
    namespace: str
    group: str
    action: str | None = None
    args: list[str] = field(default_factory=list)
    flags: dict[str, str | bool] = field(default_factory=dict)

    @property
    def command_name(self) -> str:
        parts = [self.namespace, self.group]
        if self.action:
            parts.append(self.action)
        return " ".join(parts)


@dataclass(frozen=True)
class ShellUserContext:
    user_id: str | None
    tenant_id: str | None
    role: str
    source_ip: str | None = None
    user_agent: str | None = None


class ShellResponse(BaseModel):
    command: str
    status: str
    output: str
    metadata: dict[str, Any] = Field(default_factory=dict)

