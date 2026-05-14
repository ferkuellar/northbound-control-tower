from __future__ import annotations

from auth.permissions import Permission
from models.user import UserRole

ADMIN_PERMISSIONS = frozenset(permission.value for permission in Permission)

ANALYST_PERMISSIONS = frozenset(
    {
        Permission.TENANTS_READ.value,
        Permission.CLOUD_ACCOUNTS_READ.value,
        Permission.CLOUD_ACCOUNTS_WRITE.value,
        Permission.INVENTORY_READ.value,
        Permission.INVENTORY_SCAN.value,
        Permission.FINDINGS_READ.value,
        Permission.FINDINGS_WRITE.value,
        Permission.SCORES_READ.value,
        Permission.SCORES_CALCULATE.value,
        Permission.AI_READ.value,
        Permission.AI_GENERATE.value,
        Permission.REPORTS_READ.value,
        Permission.REPORTS_GENERATE.value,
    }
)

VIEWER_PERMISSIONS = frozenset(
    {
        Permission.TENANTS_READ.value,
        Permission.CLOUD_ACCOUNTS_READ.value,
        Permission.INVENTORY_READ.value,
        Permission.FINDINGS_READ.value,
        Permission.SCORES_READ.value,
        Permission.AI_READ.value,
        Permission.REPORTS_READ.value,
    }
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    UserRole.ADMIN.value: ADMIN_PERMISSIONS,
    UserRole.ANALYST.value: ANALYST_PERMISSIONS,
    UserRole.VIEWER.value: VIEWER_PERMISSIONS,
}


def permissions_for_role(role: str) -> frozenset[str]:
    return ROLE_PERMISSIONS.get(role, frozenset())


def role_has_permission(role: str, permission: str) -> bool:
    return permission in permissions_for_role(role)
