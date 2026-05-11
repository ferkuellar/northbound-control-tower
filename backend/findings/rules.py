from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from findings.enums import FindingCategory, FindingSeverity, FindingType
from findings.schemas import FindingCandidate
from models.resource import Resource


class BaseFindingRule(ABC):
    rule_id: str
    finding_type: FindingType
    category: FindingCategory
    severity: FindingSeverity

    @abstractmethod
    def evaluate(self, resource: Resource) -> FindingCandidate | None:
        raise NotImplementedError


def _metadata(resource: Resource) -> dict[str, Any]:
    return resource.metadata_json if isinstance(resource.metadata_json, dict) else {}


def _evidence_base(resource: Resource) -> dict[str, Any]:
    return {
        "provider": resource.provider,
        "resource_id": resource.resource_id,
        "resource_category": resource.resource_type,
        "raw_type": resource.raw_type,
        "region": resource.region,
        "resource_name": resource.name,
    }


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


class MissingTagsRule(BaseFindingRule):
    rule_id = "phase6.missing_tags.v1"
    finding_type = FindingType.MISSING_TAGS
    category = FindingCategory.GOVERNANCE
    severity = FindingSeverity.MEDIUM

    def evaluate(self, resource: Resource) -> FindingCandidate | None:
        missing = []
        if resource.environment in {None, "", "unknown"}:
            missing.append("environment")
        if _is_empty(resource.owner):
            missing.append("owner")
        if _is_empty(resource.cost_center):
            missing.append("cost_center")
        if _is_empty(resource.application):
            missing.append("application")
        if not missing:
            return None
        severity_hint = "high" if resource.environment == "prod" and {"owner", "cost_center"} & set(missing) else self.severity.value
        evidence = _evidence_base(resource) | {"missing_tags": missing, "severity_hint": severity_hint}
        return FindingCandidate(
            title="Resource is missing required governance tags",
            description=f"Resource {resource.name or resource.resource_id} is missing required tags: {', '.join(missing)}.",
            evidence=evidence,
            recommendation="Add environment, owner, cost_center, and application tags through the standard tagging workflow.",
        )


class PublicExposureRule(BaseFindingRule):
    rule_id = "phase6.public_exposure.v1"
    finding_type = FindingType.PUBLIC_EXPOSURE
    category = FindingCategory.SECURITY
    severity = FindingSeverity.HIGH

    def evaluate(self, resource: Resource) -> FindingCandidate | None:
        metadata = _metadata(resource)
        reasons: list[str] = []
        if resource.exposure_level == "public":
            reasons.append("exposure_level=public")
        if metadata.get("public_ip"):
            reasons.append("public_ip_present")
        if self._allows_anywhere(metadata):
            reasons.append("allows_0.0.0.0/0")
        provider_details = metadata.get("provider_details", {})
        if isinstance(provider_details, dict) and provider_details.get("is_private") is False:
            reasons.append("public_load_balancer")
        if not reasons:
            return None
        severity_hint = self._severity(resource)
        return FindingCandidate(
            title="Resource appears publicly exposed",
            description=f"Resource {resource.name or resource.resource_id} has public exposure indicators.",
            evidence=_evidence_base(resource) | {"exposure_reasons": reasons, "severity_hint": severity_hint},
            recommendation="Validate intended exposure, restrict inbound access where possible, and ensure monitoring is enabled.",
        )

    def _severity(self, resource: Resource) -> str:
        if resource.resource_type in {"database", "identity"}:
            return FindingSeverity.CRITICAL.value
        if resource.resource_type == "network" and resource.raw_type and "LoadBalancer" in resource.raw_type:
            return FindingSeverity.MEDIUM.value
        return self.severity.value

    def _allows_anywhere(self, metadata: dict[str, Any]) -> bool:
        values = [metadata]
        provider_details = metadata.get("provider_details")
        if isinstance(provider_details, dict):
            values.append(provider_details)
        return any("0.0.0.0/0" in str(value) for value in values)


class UnattachedVolumeRule(BaseFindingRule):
    rule_id = "phase6.unattached_volume.v1"
    finding_type = FindingType.UNATTACHED_VOLUME
    category = FindingCategory.FINOPS
    severity = FindingSeverity.LOW

    def evaluate(self, resource: Resource) -> FindingCandidate | None:
        if resource.resource_type != "block_storage":
            return None
        metadata = _metadata(resource)
        attached_to = metadata.get("attached_to")
        provider_details = metadata.get("provider_details", {})
        attachments = provider_details.get("attachments") if isinstance(provider_details, dict) else None
        is_unattached = (
            resource.lifecycle_status in {"detached", "available"}
            or resource.status in {"detached", "available"}
            or _is_empty(attached_to)
            or attachments == []
        )
        if not is_unattached:
            return None
        return FindingCandidate(
            title="Block storage volume appears unattached",
            description=f"Volume {resource.name or resource.resource_id} appears unattached or available.",
            evidence=_evidence_base(resource) | {"lifecycle_status": resource.lifecycle_status, "attached_to": attached_to},
            recommendation="Validate last use, create a snapshot if required, then delete the volume or reattach it to an active workload.",
        )


class IdleComputeRule(BaseFindingRule):
    rule_id = "phase6.idle_compute.v1"
    finding_type = FindingType.IDLE_COMPUTE
    category = FindingCategory.FINOPS
    severity = FindingSeverity.MEDIUM

    def evaluate(self, resource: Resource) -> FindingCandidate | None:
        if resource.resource_type != "compute" or resource.lifecycle_status != "running":
            return None
        metadata = _metadata(resource)
        cpu = metadata.get("cpu_average_14d", metadata.get("cpu_average_7d"))
        network_in = metadata.get("network_in_average_14d")
        network_out = metadata.get("network_out_average_14d")
        if cpu is None:
            return None
        if float(cpu) >= 5:
            return None
        evidence = _evidence_base(resource) | {
            "cpu_average": cpu,
            "network_in_average_14d": network_in,
            "network_out_average_14d": network_out,
        }
        return FindingCandidate(
            title="Compute resource appears idle",
            description=f"Compute resource {resource.name or resource.resource_id} has low utilization evidence.",
            evidence=evidence,
            recommendation="Validate workload ownership and schedule, then rightsize, stop, or terminate only after owner approval.",
        )


class ObservabilityGapRule(BaseFindingRule):
    rule_id = "phase6.observability_gap.v1"
    finding_type = FindingType.OBSERVABILITY_GAP
    category = FindingCategory.OBSERVABILITY
    severity = FindingSeverity.MEDIUM

    def evaluate(self, resource: Resource) -> FindingCandidate | None:
        if resource.resource_type not in {"compute", "database", "network"}:
            return None
        metadata = _metadata(resource)
        has_monitoring_keys = "monitoring_enabled" in metadata or "alarms_count" in metadata
        gap = metadata.get("monitoring_enabled") is False or metadata.get("alarms_count") == 0
        prod_without_metadata = resource.environment == "prod" and not has_monitoring_keys
        if not gap and not prod_without_metadata:
            return None
        severity_hint = FindingSeverity.HIGH.value if prod_without_metadata else self.severity.value
        return FindingCandidate(
            title="Resource may lack basic monitoring coverage",
            description=f"Resource {resource.name or resource.resource_id} has missing or insufficient monitoring indicators.",
            evidence=_evidence_base(resource)
            | {
                "monitoring_enabled": metadata.get("monitoring_enabled"),
                "alarms_count": metadata.get("alarms_count"),
                "severity_hint": severity_hint,
            },
            recommendation="Enable baseline monitoring and attach actionable alarms before relying on this resource for production workloads.",
        )
