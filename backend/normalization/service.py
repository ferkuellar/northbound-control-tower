from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from normalization.enums import ExposureLevel, Provider, ResourceCategory
from normalization.metadata import sanitize_metadata
from normalization.schemas import NormalizedResource
from normalization.validators import (
    infer_exposure_level,
    normalize_criticality,
    normalize_environment,
    normalize_lifecycle_status,
)

logger = logging.getLogger(__name__)

TAG_KEY_ALIASES = {
    "env": "environment",
    "environment": "environment",
    "owner": "owner",
    "costcenter": "cost_center",
    "cost_center": "cost_center",
    "app": "application",
    "application": "application",
    "service": "service_name",
    "criticality": "criticality",
}


class ResourceNormalizationService:
    def normalize(
        self,
        resource: dict[str, Any],
        *,
        tenant_id: uuid.UUID | None = None,
        cloud_account_id: uuid.UUID | None = None,
        account_id: str | None = None,
    ) -> NormalizedResource:
        try:
            provider = Provider(resource["provider"])
        except Exception:
            provider = Provider.AWS if resource.get("provider") == "aws" else Provider.OCI

        resource_category = self._resource_category(resource)
        tags = self.normalize_tags(provider, resource.get("tags"))
        flat_tags = self._flat_tags(tags)
        metadata = sanitize_metadata(resource.get("metadata"))

        lifecycle_status = normalize_lifecycle_status(resource.get("lifecycle_status") or resource.get("status"))
        exposure_level = self._exposure_level(resource, metadata)
        environment = normalize_environment(resource.get("environment") or self._tag_value(flat_tags, "environment"))
        criticality = normalize_criticality(resource.get("criticality") or self._tag_value(flat_tags, "criticality"))
        raw_type = resource.get("raw_type") or "unknown"
        region = resource.get("region") or "global"
        resource_id = str(resource.get("resource_id") or "unknown")

        normalized = NormalizedResource(
            provider=provider,
            resource_category=resource_category,
            resource_id=resource_id,
            raw_type=raw_type,
            name=resource.get("name") or resource_id,
            region=region,
            account_id=account_id or resource.get("account_id"),
            compartment_id=resource.get("compartment_id") or metadata.get("provider_details", {}).get("compartment_id"),
            tenant_id=tenant_id,
            cloud_account_id=cloud_account_id,
            availability_zone=resource.get("availability_zone"),
            availability_domain=resource.get("availability_domain") or resource.get("availability_zone"),
            lifecycle_status=lifecycle_status,
            exposure_level=exposure_level,
            environment=environment,
            criticality=criticality,
            owner=resource.get("owner") or self._tag_value(flat_tags, "owner"),
            cost_center=resource.get("cost_center") or self._tag_value(flat_tags, "cost_center"),
            application=resource.get("application") or self._tag_value(flat_tags, "application"),
            service_name=resource.get("service_name") or self._tag_value(flat_tags, "service_name"),
            tags=tags,
            metadata=metadata,
            relationships=resource.get("relationships") or {},
            discovered_at=resource.get("discovered_at") or datetime.now(UTC),
        )
        normalized.fingerprint = self.fingerprint(normalized)
        return normalized

    def prepare_upsert_payload(
        self,
        resource: dict[str, Any],
        *,
        tenant_id: uuid.UUID,
        cloud_account_id: uuid.UUID,
        account_id: str | None = None,
    ) -> dict[str, Any]:
        normalized = self.normalize(
            resource,
            tenant_id=tenant_id,
            cloud_account_id=cloud_account_id,
            account_id=account_id,
        )
        return normalized.model_dump(mode="python")

    def normalize_many(
        self,
        resources: list[dict[str, Any]],
        *,
        tenant_id: uuid.UUID,
        cloud_account_id: uuid.UUID,
        account_id: str | None = None,
    ) -> list[dict[str, Any]]:
        normalized_resources: list[dict[str, Any]] = []
        for resource in resources:
            try:
                normalized_resources.append(
                    self.prepare_upsert_payload(
                        resource,
                        tenant_id=tenant_id,
                        cloud_account_id=cloud_account_id,
                        account_id=account_id,
                    )
                )
            except Exception:
                logger.exception(
                    "Resource normalization failed",
                    extra={
                        "provider": resource.get("provider"),
                        "resource_id": resource.get("resource_id"),
                        "raw_type": resource.get("raw_type"),
                        "cloud_account_id": str(cloud_account_id),
                        "tenant_id": str(tenant_id),
                    },
                )
                normalized_resources.append(
                    self.prepare_upsert_payload(
                        {
                            "provider": resource.get("provider") or Provider.AWS.value,
                            "resource_category": ResourceCategory.UNKNOWN.value,
                            "resource_id": resource.get("resource_id") or "unknown",
                            "raw_type": resource.get("raw_type") or "unknown",
                            "name": resource.get("name"),
                            "region": resource.get("region") or "global",
                            "metadata": {"normalization_error": True},
                        },
                        tenant_id=tenant_id,
                        cloud_account_id=cloud_account_id,
                        account_id=account_id,
                    )
                )
        return normalized_resources

    def normalize_tags(self, provider: Provider, tags: Any) -> dict[str, Any]:
        if provider == Provider.AWS:
            if isinstance(tags, list):
                return {str(tag.get("Key")): tag.get("Value", "") for tag in tags if tag.get("Key")}
            return tags if isinstance(tags, dict) else {}
        if provider == Provider.OCI:
            if not isinstance(tags, dict):
                return {"freeform": {}, "defined": {}, "flat": {}}
            freeform = tags.get("freeform") or tags.get("freeform_tags") or {}
            defined = tags.get("defined") or tags.get("defined_tags") or {}
            return {
                "freeform": freeform if isinstance(freeform, dict) else {},
                "defined": defined if isinstance(defined, dict) else {},
                "flat": self._flatten_oci_tags(freeform, defined),
            }
        return tags if isinstance(tags, dict) else {}

    def fingerprint(self, resource: NormalizedResource) -> str:
        parts = [
            resource.provider,
            str(resource.cloud_account_id or ""),
            resource.region,
            resource.resource_id,
            resource.raw_type,
        ]
        return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()

    def _resource_category(self, resource: dict[str, Any]) -> ResourceCategory:
        value = resource.get("resource_category") or resource.get("resource_type")
        try:
            return ResourceCategory(value)
        except Exception:
            return ResourceCategory.UNKNOWN

    def _exposure_level(self, resource: dict[str, Any], metadata: dict[str, Any]) -> ExposureLevel:
        try:
            return ExposureLevel(resource["exposure_level"])
        except Exception:
            return infer_exposure_level(metadata)

    def _flat_tags(self, tags: dict[str, Any]) -> dict[str, Any]:
        if "flat" in tags and isinstance(tags["flat"], dict):
            return {str(key).lower(): value for key, value in tags["flat"].items()}
        return {str(key).lower(): value for key, value in tags.items() if not isinstance(value, dict)}

    def _tag_value(self, flat_tags: dict[str, Any], normalized_key: str) -> Any:
        for key, value in flat_tags.items():
            alias = TAG_KEY_ALIASES.get(key.replace("-", "_").replace(" ", "_").lower())
            if alias == normalized_key:
                return value
        return None

    def _flatten_oci_tags(self, freeform: Any, defined: Any) -> dict[str, Any]:
        flat: dict[str, Any] = {}
        if isinstance(freeform, dict):
            flat.update(freeform)
        if isinstance(defined, dict):
            for namespace, values in defined.items():
                if isinstance(values, dict):
                    for key, value in values.items():
                        flat[f"{namespace}.{key}"] = value
                        flat.setdefault(key, value)
        return flat
