from __future__ import annotations

from enum import StrEnum


class CloudShellAuditStatus(StrEnum):
    RECEIVED = "RECEIVED"
    AUTHORIZED = "AUTHORIZED"
    REJECTED = "REJECTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    BLOCKED = "BLOCKED"


class CloudShellRiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

