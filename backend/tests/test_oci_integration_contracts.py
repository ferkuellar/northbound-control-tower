import pytest

from api.schemas.inventory import CloudAccountRead
from collectors.oci.errors import OCIConfigurationError
from collectors.oci.session import OCISessionFactory
from models.cloud_account import CloudAccount, CloudAccountAuthType, CloudProvider


def test_cloud_provider_enum_supports_aws_and_oci() -> None:
    assert CloudProvider.AWS.value == "aws"
    assert CloudProvider.OCI.value == "oci"


def test_oci_session_factory_requires_api_key_fields() -> None:
    cloud_account = CloudAccount(
        provider=CloudProvider.OCI.value,
        name="OCI Test",
        auth_type=CloudAccountAuthType.OCI_API_KEY.value,
        default_region="us-ashburn-1",
    )

    with pytest.raises(OCIConfigurationError) as exc_info:
        OCISessionFactory(cloud_account)._validate_api_key_fields()

    assert "tenancy_ocid" in str(exc_info.value)
    assert "user_ocid" in str(exc_info.value)
    assert "fingerprint" in str(exc_info.value)
    assert "private_key" in str(exc_info.value)


def test_oci_session_factory_uses_scoped_compartment_before_tenancy() -> None:
    cloud_account = CloudAccount(
        provider=CloudProvider.OCI.value,
        name="OCI Test",
        auth_type=CloudAccountAuthType.OCI_API_KEY.value,
        default_region="us-ashburn-1",
        compartment_ocid="ocid1.compartment.oc1..scope",
    )

    root = OCISessionFactory(cloud_account).root_compartment_id({"tenancy": "ocid1.tenancy.oc1..root"})

    assert root == "ocid1.compartment.oc1..scope"


def test_cloud_account_read_does_not_expose_oci_secrets() -> None:
    field_names = set(CloudAccountRead.model_fields)

    assert "access_key_id" not in field_names
    assert "secret_access_key" not in field_names
    assert "private_key" not in field_names
    assert "private_key_passphrase" not in field_names
    assert "fingerprint" not in field_names
    assert "user_ocid" not in field_names
    assert "tenancy_ocid" not in field_names
