from __future__ import annotations

import shlex

from cloud_shell.errors import CommandBlockedError, CommandParseError
from cloud_shell.schemas import ParsedCommand

BLOCKED_TOKENS = {
    "bash",
    "sh",
    "zsh",
    "powershell",
    "pwsh",
    "cmd",
    "cat",
    "printenv",
    "env",
    "aws",
    "oci",
}

BLOCKED_PHRASES = {
    "terraform apply -auto-approve",
    "apply -auto-approve",
    "aws s3 rm",
    "aws iam delete-role",
}

GROUP_ONLY_COMMANDS = {"approve", "reject"}


class CommandParser:
    """Parses only Northbound controlled commands."""

    def parse(self, raw_command: str) -> ParsedCommand:
        command = raw_command.strip()
        if not command:
            raise CommandParseError("Command is empty. Type: nb help")

        normalized = command.lower()
        if normalized.startswith("nb terraform destroy"):
            raise CommandBlockedError("Command blocked. Terraform destroy is not available from Northbound Cloud Shell.")
        if "../" in command or "..\\" in command or "/etc/passwd" in normalized or ".env" in normalized:
            raise CommandBlockedError("Command blocked. Only Northbound controlled commands are allowed.")
        if any(phrase in normalized for phrase in BLOCKED_PHRASES):
            raise CommandBlockedError("Command blocked. Only Northbound controlled commands are allowed.")

        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            raise CommandParseError("Command could not be parsed.") from exc

        if not tokens:
            raise CommandParseError("Command is empty. Type: nb help")
        if tokens[0].lower() != "nb":
            raise CommandBlockedError("Command blocked. Only Northbound controlled commands are allowed.")
        if any(token.lower() in BLOCKED_TOKENS for token in tokens):
            raise CommandBlockedError("Command blocked. Only Northbound controlled commands are allowed.")
        if len(tokens) < 2:
            raise CommandParseError("Incomplete command. Type: nb help")

        group = tokens[1].lower()
        action: str | None = None
        args_start = 2
        if group not in GROUP_ONLY_COMMANDS and len(tokens) >= 3 and not tokens[2].startswith("--"):
            action = tokens[2].lower()
            args_start = 3

        args: list[str] = []
        flags: dict[str, str | bool] = {}
        index = args_start
        while index < len(tokens):
            token = tokens[index]
            if token.startswith("--"):
                key = token[2:].strip().replace("-", "_")
                if not key:
                    raise CommandParseError("Invalid flag.")
                next_index = index + 1
                if next_index < len(tokens) and not tokens[next_index].startswith("--"):
                    flags[key] = tokens[next_index]
                    index += 2
                else:
                    flags[key] = True
                    index += 1
            else:
                args.append(token)
                index += 1

        return ParsedCommand(namespace="nb", group=group, action=action, args=args, flags=flags)

