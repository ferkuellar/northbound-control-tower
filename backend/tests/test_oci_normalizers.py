from collectors.oci.normalizers import (
    normalize_block_volume,
    normalize_compartment,
    normalize_compute_instance,
    normalize_network_resource,
)


def test_normalize_oci_compute_instance_preserves_tags() -> None:
    resource = normalize_compute_instance(
        {
            "id": "ocid1.instance.oc1..example",
            "display_name": "app-1",
            "lifecycle_state": "RUNNING",
            "availability_domain": "AD-1",
            "shape": "VM.Standard.E4.Flex",
            "compartment_id": "ocid1.compartment.oc1..example",
            "freeform_tags": {"env": "dev"},
            "defined_tags": {"Operations": {"Owner": "platform"}},
        },
        "us-ashburn-1",
    )

    assert resource["provider"] == "oci"
    assert resource["resource_type"] == "compute"
    assert resource["resource_id"] == "ocid1.instance.oc1..example"
    assert resource["name"] == "app-1"
    assert resource["availability_zone"] == "AD-1"
    assert resource["tags"]["freeform_tags"]["env"] == "dev"
    assert resource["tags"]["defined_tags"]["Operations"]["Owner"] == "platform"
    assert resource["metadata"]["shape"] == "VM.Standard.E4.Flex"


def test_normalize_oci_block_volume() -> None:
    resource = normalize_block_volume(
        {
            "id": "ocid1.volume.oc1..example",
            "display_name": "data-volume",
            "lifecycle_state": "AVAILABLE",
            "availability_domain": "AD-1",
            "size_in_gbs": 100,
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        "us-ashburn-1",
    )

    assert resource["resource_type"] == "block_storage"
    assert resource["resource_id"] == "ocid1.volume.oc1..example"
    assert resource["metadata"]["size_gb"] == 100


def test_normalize_oci_network_resource() -> None:
    resource = normalize_network_resource(
        {
            "id": "ocid1.vcn.oc1..example",
            "display_name": "main-vcn",
            "lifecycle_state": "AVAILABLE",
            "cidr_block": "10.0.0.0/16",
            "compartment_id": "ocid1.compartment.oc1..example",
        },
        "us-ashburn-1",
        raw_type="OCI::Core::Vcn",
    )

    assert resource["resource_type"] == "network"
    assert resource["raw_type"] == "OCI::Core::Vcn"
    assert resource["metadata"]["cidr_block"] == "10.0.0.0/16"


def test_normalize_oci_compartment() -> None:
    resource = normalize_compartment(
        {
            "id": "ocid1.compartment.oc1..example",
            "name": "Security",
            "description": "Security resources",
            "lifecycle_state": "ACTIVE",
        },
        "us-ashburn-1",
    )

    assert resource["resource_type"] == "identity"
    assert resource["name"] == "Security"
    assert resource["status"] == "ACTIVE"
