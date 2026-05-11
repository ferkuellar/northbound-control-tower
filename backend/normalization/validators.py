from __future__ import annotations

from typing import Any

from normalization.enums import Criticality, Environment, ExposureLevel, ResourceLifecycleStatus

ENVIRONMENT_ALIASES = {
    "production": Environment.PROD,
    "prod": Environment.PROD,
    "development": Environment.DEV,
    "dev": Environment.DEV,
    "qa": Environment.QA,
    "test": Environment.TEST,
    "testing": Environment.TEST,
    "sandbox": Environment.SANDBOX,
    "shared": Environment.SHARED,
}

CRITICALITY_ALIASES = {
    "low": Criticality.LOW,
    "medium": Criticality.MEDIUM,
    "med": Criticality.MEDIUM,
    "high": Criticality.HIGH,
    "critical": Criticality.CRITICAL,
    "crit": Criticality.CRITICAL,
}

LIFECYCLE_STATUS_ALIASES = {
    "running": ResourceLifecycleStatus.RUNNING,
    "available": ResourceLifecycleStatus.AVAILABLE,
    "active": ResourceLifecycleStatus.ACTIVE,
    "enabled": ResourceLifecycleStatus.ACTIVE,
    "ok": ResourceLifecycleStatus.ACTIVE,
    "in-use": ResourceLifecycleStatus.ATTACHED,
    "attached": ResourceLifecycleStatus.ATTACHED,
    "detached": ResourceLifecycleStatus.DETACHED,
    "stopped": ResourceLifecycleStatus.STOPPED,
    "stopping": ResourceLifecycleStatus.STOPPED,
    "terminated": ResourceLifecycleStatus.DELETED,
    "deleted": ResourceLifecycleStatus.DELETED,
    "deleting": ResourceLifecycleStatus.DELETED,
    "inactive": ResourceLifecycleStatus.INACTIVE,
    "alarm": ResourceLifecycleStatus.ACTIVE,
    "insufficient_data": ResourceLifecycleStatus.UNKNOWN,
}


def normalize_environment(value: Any) -> Environment:
    if value is None:
        return Environment.UNKNOWN
    return ENVIRONMENT_ALIASES.get(str(value).strip().lower(), Environment.UNKNOWN)


def normalize_criticality(value: Any) -> Criticality:
    if value is None:
        return Criticality.UNKNOWN
    return CRITICALITY_ALIASES.get(str(value).strip().lower(), Criticality.UNKNOWN)


def normalize_lifecycle_status(value: Any) -> ResourceLifecycleStatus:
    if value is None:
        return ResourceLifecycleStatus.UNKNOWN
    return LIFECYCLE_STATUS_ALIASES.get(str(value).strip().lower(), ResourceLifecycleStatus.UNKNOWN)


def infer_exposure_level(metadata: dict[str, Any]) -> ExposureLevel:
    if metadata.get("public_ip"):
        return ExposureLevel.PUBLIC
    if metadata.get("private_ip") or metadata.get("subnet_id") or metadata.get("vpc_id") or metadata.get("vcn_id"):
        return ExposureLevel.INTERNAL
    return ExposureLevel.UNKNOWN
