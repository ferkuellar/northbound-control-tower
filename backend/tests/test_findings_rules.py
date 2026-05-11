import uuid

from findings.enums import FindingType
from findings.rules import (
    IdleComputeRule,
    MissingTagsRule,
    ObservabilityGapRule,
    PublicExposureRule,
    UnattachedVolumeRule,
)
from models.resource import Resource


def _resource(**overrides) -> Resource:
    data = {
        "id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "cloud_account_id": uuid.uuid4(),
        "provider": "aws",
        "resource_type": "compute",
        "resource_id": "res-1",
        "name": "res-1",
        "region": "us-east-1",
        "raw_type": "AWS::EC2::Instance",
        "lifecycle_status": "running",
        "exposure_level": "private",
        "environment": "unknown",
        "metadata_json": {},
    }
    data.update(overrides)
    return Resource(**data)


def test_missing_tags_rule_detects_missing_required_tags() -> None:
    candidate = MissingTagsRule().evaluate(_resource(owner=None, cost_center=None, application=None))

    assert candidate is not None
    assert candidate.evidence["missing_tags"] == ["environment", "owner", "cost_center", "application"]


def test_public_exposure_rule_detects_public_resource() -> None:
    candidate = PublicExposureRule().evaluate(_resource(exposure_level="public", metadata_json={"public_ip": "203.0.113.10"}))

    assert candidate is not None
    assert candidate.evidence["severity_hint"] == "high"


def test_unattached_volume_rule_detects_available_block_storage() -> None:
    candidate = UnattachedVolumeRule().evaluate(
        _resource(resource_type="block_storage", lifecycle_status="available", raw_type="AWS::EC2::Volume")
    )

    assert candidate is not None
    assert "snapshot" in candidate.recommendation


def test_idle_compute_requires_metrics() -> None:
    assert IdleComputeRule().evaluate(_resource()) is None


def test_idle_compute_detects_low_cpu_with_metrics() -> None:
    candidate = IdleComputeRule().evaluate(_resource(metadata_json={"cpu_average_7d": 2.0}))

    assert candidate is not None
    assert FindingType.IDLE_COMPUTE.value in IdleComputeRule().finding_type.value


def test_observability_gap_detects_missing_monitoring_for_prod() -> None:
    candidate = ObservabilityGapRule().evaluate(_resource(environment="prod", metadata_json={}))

    assert candidate is not None
    assert candidate.evidence["severity_hint"] == "high"
