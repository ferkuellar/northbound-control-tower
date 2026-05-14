from __future__ import annotations

from enum import StrEnum


class Permission(StrEnum):
    USERS_READ = "users:read"
    USERS_WRITE = "users:write"
    TENANTS_READ = "tenants:read"
    TENANTS_WRITE = "tenants:write"
    CLOUD_ACCOUNTS_READ = "cloud_accounts:read"
    CLOUD_ACCOUNTS_WRITE = "cloud_accounts:write"
    INVENTORY_READ = "inventory:read"
    INVENTORY_SCAN = "inventory:scan"
    FINDINGS_READ = "findings:read"
    FINDINGS_WRITE = "findings:write"
    SCORES_READ = "scores:read"
    SCORES_CALCULATE = "scores:calculate"
    AI_READ = "ai:read"
    AI_GENERATE = "ai:generate"
    REPORTS_READ = "reports:read"
    REPORTS_GENERATE = "reports:generate"
    AUDIT_READ = "audit:read"


PERMISSION_REGISTRY: frozenset[str] = frozenset(permission.value for permission in Permission)


def normalize_permission(permission: Permission | str) -> str:
    value = permission.value if isinstance(permission, Permission) else permission
    if value not in PERMISSION_REGISTRY:
        raise ValueError(f"Unknown permission: {value}")
    return value
