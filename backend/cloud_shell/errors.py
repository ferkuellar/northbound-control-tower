from __future__ import annotations


class CloudShellError(Exception):
    """Base controlled shell error."""


class CommandBlockedError(CloudShellError):
    """Raised when command input violates the controlled shell boundary."""


class CommandParseError(CloudShellError):
    """Raised when a command cannot be parsed into a Northbound command."""


class CommandNotFoundError(CloudShellError):
    """Raised when a parsed command is not registered."""


class CommandAuthorizationError(CloudShellError):
    """Raised when a user role cannot execute a command."""

