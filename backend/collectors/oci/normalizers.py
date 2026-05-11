from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from models.resource import ResourceType


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
