from __future__ import annotations

from cloud_shell.errors import CommandAuthorizationError
from cloud_shell.schemas import ShellUserContext


ROLE_RANK: dict[str, int] = {
    "VIEWER": 10,
    "ANALYST": 20,
    "OPERATOR": 20,
    "APPROVER": 30,
    "ADMIN": 40,
    "BREAKGLASS_ADMIN": 50,
}


class CloudShellAuthorizationService:
    """RBAC guard for controlled shell commands."""

    def authorize(self, *, user_context: ShellUserContext, required_role: str) -> None:
        user_rank = ROLE_RANK.get(user_context.role, 0)
        required_rank = ROLE_RANK.get(required_role, 999)
        if user_rank < required_rank:
            raise CommandAuthorizationError("Insufficient role for this Northbound command.")

