from __future__ import annotations

from typing import Any

STANDARD_METADATA_KEYS = {
    "cpu_count",
    "memory_gb",
    "shape",
    "instance_type",
    "storage_gb",
    "engine",
    "version",
    "public_ip",
    "private_ip",
    "vpc_id",
    "vcn_id",
    "subnet_id",
    "security_groups",
    "nsgs",
    "attached_to",
    "alarm_state",
    "created_time",
    "updated_time",
}

METADATA_ALIASES = {
    "size_gib": "storage_gb",
    "size_gb": "storage_gb",
    "engine_version": "version",
    "private_ip_address": "private_ip",
    "public_ip_address": "public_ip",
    "state": "alarm_state",
}

SECRET_METADATA_KEYS = {
    "access_key",
    "access_key_id",
    "secret",
    "secret_access_key",
    "token",
    "password",
    "private_key",
    "private_key_passphrase",
    "fingerprint",
    "key_content",
}


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(metadata, dict):
        return {}
    sanitized: dict[str, Any] = {}
    provider_details: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = METADATA_ALIASES.get(key, key)
        if normalized_key.lower() in SECRET_METADATA_KEYS:
            continue
        if normalized_key in STANDARD_METADATA_KEYS:
            sanitized[normalized_key] = value
        else:
            provider_details[key] = value
    if provider_details:
        sanitized["provider_details"] = provider_details
    return sanitized
