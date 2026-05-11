from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from models.resource import ResourceType
from normalization.contracts import BaseProviderNormalizer


def _as_dict(resource: Any) -> dict[str, Any]:
    if isinstance(resource, dict):
        return resource
    return vars(resource)


def _oci_tags(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "freeform_tags": resource.get("freeform_tags") or {},
        "defined_tags": resource.get("defined_tags") or {},
    }


def _base(
    *,
    resource_type: ResourceType,
    resource_id: str,
    raw_type: str,
    region: str | None,
    name: str | None,
    availability_zone: str | None = None,
    status: str | None = None,
    tags: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "provider": "oci",
        "resource_type": resource_type.value,
        "resource_id": resource_id,
        "name": name,
        "region": region,
        "availability_zone": availability_zone,
        "raw_type": raw_type,
        "status": status,
        "tags": tags or {},
        "metadata": metadata or {},
        "discovered_at": datetime.now(UTC),
    }


def normalize_compute_instance(instance: Any, region: str) -> dict[str, Any]:
    data = _as_dict(instance)
    return _base(
        resource_type=ResourceType.COMPUTE,
        resource_id=data["id"],
        name=data.get("display_name"),
        region=region,
        availability_zone=data.get("availability_domain"),
        raw_type="OCI::Core::Instance",
        status=data.get("lifecycle_state"),
        tags=_oci_tags(data),
        metadata={"shape": data.get("shape"), "compartment_id": data.get("compartment_id")},
    )


def normalize_block_volume(volume: Any, region: str, *, raw_type: str = "OCI::Core::Volume") -> dict[str, Any]:
    data = _as_dict(volume)
    return _base(
        resource_type=ResourceType.BLOCK_STORAGE,
        resource_id=data["id"],
        name=data.get("display_name"),
        region=region,
        availability_zone=data.get("availability_domain"),
        raw_type=raw_type,
        status=data.get("lifecycle_state"),
        tags=_oci_tags(data),
        metadata={"size_gb": data.get("size_in_gbs"), "compartment_id": data.get("compartment_id")},
    )


def normalize_network_resource(resource: Any, region: str, *, raw_type: str) -> dict[str, Any]:
    data = _as_dict(resource)
    return _base(
        resource_type=ResourceType.NETWORK,
        resource_id=data["id"],
        name=data.get("display_name"),
        region=region,
        raw_type=raw_type,
        status=data.get("lifecycle_state"),
        tags=_oci_tags(data),
        metadata={"compartment_id": data.get("compartment_id"), "cidr_block": data.get("cidr_block")},
    )


def normalize_load_balancer(load_balancer: Any, region: str) -> dict[str, Any]:
    data = _as_dict(load_balancer)
    return _base(
        resource_type=ResourceType.NETWORK,
        resource_id=data["id"],
        name=data.get("display_name"),
        region=region,
        raw_type="OCI::LoadBalancer::LoadBalancer",
        status=data.get("lifecycle_state"),
        tags=_oci_tags(data),
        metadata={"compartment_id": data.get("compartment_id"), "shape_name": data.get("shape_name")},
    )


def normalize_compartment(compartment: Any, region: str) -> dict[str, Any]:
    data = _as_dict(compartment)
    return _base(
        resource_type=ResourceType.IDENTITY,
        resource_id=data["id"],
        name=data.get("name"),
        region=region,
        raw_type="OCI::Identity::Compartment",
        status=data.get("lifecycle_state"),
        tags=_oci_tags(data),
        metadata={"compartment_id": data.get("compartment_id"), "description": data.get("description")},
    )


def normalize_identity_resource(resource: Any, region: str, *, raw_type: str) -> dict[str, Any]:
    data = _as_dict(resource)
    return _base(
        resource_type=ResourceType.IDENTITY,
        resource_id=data["id"],
        name=data.get("name"),
        region=region,
        raw_type=raw_type,
        status=data.get("lifecycle_state"),
        metadata={"compartment_id": data.get("compartment_id"), "description": data.get("description")},
    )


def normalize_alarm(alarm: Any, region: str) -> dict[str, Any]:
    data = _as_dict(alarm)
    return _base(
        resource_type=ResourceType.MONITORING,
        resource_id=data["id"],
        name=data.get("display_name"),
        region=region,
        raw_type="OCI::Monitoring::Alarm",
        status=data.get("lifecycle_state"),
        tags=_oci_tags(data),
        metadata={
            "compartment_id": data.get("compartment_id"),
            "namespace": data.get("namespace"),
            "query": data.get("query"),
            "severity": data.get("severity"),
        },
    )


class OCIProviderNormalizer(BaseProviderNormalizer):
    def normalize_compute(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        return normalize_compute_instance(resource, region or "global")

    def normalize_block_storage(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        return normalize_block_volume(resource, region or "global")

    def normalize_object_storage(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        return self.normalize_unknown(resource, region)

    def normalize_database(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        return self.normalize_unknown(resource, region)

    def normalize_network(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        data = _as_dict(resource)
        raw_type = data.get("raw_type") or "OCI::Core::Network"
        if "shape_name" in data:
            return normalize_load_balancer(resource, region or "global")
        return normalize_network_resource(resource, region or "global", raw_type=raw_type)

    def normalize_identity(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        data = _as_dict(resource)
        if data.get("compartment_id") or data.get("description"):
            return normalize_compartment(resource, region or "global")
        return normalize_identity_resource(resource, region or "global", raw_type=data.get("raw_type") or "OCI::Identity::Resource")

    def normalize_monitoring(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        return normalize_alarm(resource, region or "global")

    def normalize_unknown(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        data = _as_dict(resource)
        return _base(
            resource_type=ResourceType.UNKNOWN,
            resource_id=str(data.get("id") or "unknown"),
            name=data.get("display_name") or data.get("name"),
            region=region or "global",
            raw_type=str(data.get("raw_type") or "OCI::Unknown"),
            status=data.get("lifecycle_state") or "unknown",
            tags=_oci_tags(data),
            metadata={"provider_details": data},
        )
