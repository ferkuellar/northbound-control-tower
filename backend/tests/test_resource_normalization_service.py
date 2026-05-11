import uuid

from normalization.enums import Criticality, Environment, ExposureLevel, ResourceCategory, ResourceLifecycleStatus
from normalization.service import ResourceNormalizationService


def test_aws_tag_normalization_and_derived_fields() -> None:
    service = ResourceNormalizationService()

    resource = service.normalize(
        {
            "provider": "aws",
            "resource_type": "compute",
            "resource_id": "i-123",
            "raw_type": "AWS::EC2::Instance",
            "region": "us-east-1",
            "status": "running",
            "tags": [
                {"Key": "env", "Value": "prod"},
                {"Key": "owner", "Value": "platform"},
                {"Key": "cost_center", "Value": "finops"},
                {"Key": "application", "Value": "tower"},
                {"Key": "criticality", "Value": "critical"},
            ],
            "metadata": {"private_ip_address": "10.0.0.10", "instance_type": "t3.micro"},
        },
        tenant_id=uuid.uuid4(),
        cloud_account_id=uuid.uuid4(),
    )

    assert resource.name == "i-123"
    assert resource.resource_category == ResourceCategory.COMPUTE
    assert resource.lifecycle_status == ResourceLifecycleStatus.RUNNING
    assert resource.exposure_level == ExposureLevel.INTERNAL
    assert resource.environment == Environment.PROD
    assert resource.criticality == Criticality.CRITICAL
    assert resource.owner == "platform"
    assert resource.cost_center == "finops"
    assert resource.application == "tower"
    assert resource.metadata["private_ip"] == "10.0.0.10"
    assert resource.fingerprint


def test_oci_tag_normalization_preserves_freeform_defined_and_flat() -> None:
    service = ResourceNormalizationService()

    resource = service.normalize(
        {
            "provider": "oci",
            "resource_type": "network",
            "resource_id": "ocid1.vcn.oc1..example",
            "raw_type": "OCI::Core::VCN",
            "name": "main-vcn",
            "region": "us-ashburn-1",
            "status": "AVAILABLE",
            "tags": {
                "freeform_tags": {"env": "dev"},
                "defined_tags": {"Operations": {"Owner": "network-team"}},
            },
            "metadata": {"compartment_id": "ocid1.compartment.oc1..example", "cidr_block": "10.0.0.0/16"},
        },
        tenant_id=uuid.uuid4(),
        cloud_account_id=uuid.uuid4(),
    )

    assert resource.tags["freeform"]["env"] == "dev"
    assert resource.tags["defined"]["Operations"]["Owner"] == "network-team"
    assert resource.tags["flat"]["Owner"] == "network-team"
    assert resource.environment == Environment.DEV
    assert resource.compartment_id == "ocid1.compartment.oc1..example"


def test_fingerprint_is_deterministic_for_same_identity() -> None:
    service = ResourceNormalizationService()
    cloud_account_id = uuid.uuid4()
    payload = {
        "provider": "aws",
        "resource_type": "object_storage",
        "resource_id": "nct-bucket",
        "raw_type": "AWS::S3::Bucket",
        "name": "nct-bucket",
        "region": "global",
    }

    first = service.normalize(payload, tenant_id=uuid.uuid4(), cloud_account_id=cloud_account_id)
    second = service.normalize(payload, tenant_id=uuid.uuid4(), cloud_account_id=cloud_account_id)

    assert first.fingerprint == second.fingerprint


def test_unknown_resource_is_valid_and_uses_unknown_enums() -> None:
    service = ResourceNormalizationService()

    resource = service.normalize(
        {
            "provider": "aws",
            "resource_id": "mystery-1",
            "metadata": {"secret_access_key": "SHOULD_NOT_PERSIST", "custom": "value"},
        },
        tenant_id=uuid.uuid4(),
        cloud_account_id=uuid.uuid4(),
    )

    assert resource.resource_category == ResourceCategory.UNKNOWN
    assert resource.lifecycle_status == ResourceLifecycleStatus.UNKNOWN
    assert resource.raw_type == "unknown"
    assert resource.name == "mystery-1"
    assert "secret_access_key" not in resource.metadata
    assert resource.metadata["provider_details"]["custom"] == "value"
