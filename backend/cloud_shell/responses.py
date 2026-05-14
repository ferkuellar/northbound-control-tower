from __future__ import annotations

from typing import Any

from cloud_shell.schemas import ShellResponse


class ShellResponseBuilder:
    """Builder for consistent terminal and structured shell responses."""

    def __init__(self, command: str) -> None:
        self.command = command
        self.status = "success"
        self.lines: list[str] = []
        self.metadata: dict[str, Any] = {}

    def with_status(self, status: str) -> "ShellResponseBuilder":
        self.status = status
        return self

    def line(self, value: str = "") -> "ShellResponseBuilder":
        self.lines.append(value)
        return self

    def meta(self, key: str, value: Any) -> "ShellResponseBuilder":
        self.metadata[key] = value
        return self

    def build(self) -> ShellResponse:
        return ShellResponse(
            command=self.command,
            status=self.status,
            output="\n".join(self.lines).strip("\n"),
            metadata=self.metadata,
        )

