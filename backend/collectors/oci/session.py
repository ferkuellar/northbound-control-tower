from __future__ import annotations

from oci import config as oci_config
from oci.signer import Signer

from collectors.oci.errors import OCIConfigurationError
from models.cloud_account import CloudAccount, CloudAccountAuthType


class OCISessionFactory:
    def __init__(self, cloud_account: CloudAccount) -> None:
        self.cloud_account = cloud_account

    def create_config(self) -> dict[str, str]:
        auth_type = CloudAccountAuthType(self.cloud_account.auth_type)
        if auth_type == CloudAccountAuthType.OCI_CONFIG:
            config = oci_config.from_file()
            if self.cloud_account.region:
                config["region"] = self.cloud_account.region
            oci_config.validate_config(config)
            return config
        if auth_type == CloudAccountAuthType.OCI_API_KEY:
            self._validate_api_key_fields()
            config = {
                "tenancy": self.cloud_account.tenancy_ocid,
                "user": self.cloud_account.user_ocid,
                "fingerprint": self.cloud_account.fingerprint,
                "key_content": self.cloud_account.private_key,
                "region": self.cloud_account.region or self.cloud_account.default_region,
            }
            if self.cloud_account.private_key_passphrase:
                config["pass_phrase"] = self.cloud_account.private_key_passphrase
            oci_config.validate_config(config)
            return config
        raise OCIConfigurationError("Unsupported OCI auth type")

    def root_compartment_id(self, config: dict[str, str]) -> str:
        root_compartment = self.cloud_account.compartment_ocid or config.get("tenancy")
        if not root_compartment:
            raise OCIConfigurationError("OCI tenancy or compartment OCID is required")
        return root_compartment

    def signer(self, config: dict[str, str]) -> Signer:
        return Signer(
            tenancy=config["tenancy"],
            user=config["user"],
            fingerprint=config["fingerprint"],
            private_key_file_location=config.get("key_file"),
            private_key_content=config.get("key_content"),
            pass_phrase=config.get("pass_phrase"),
        )

    def _validate_api_key_fields(self) -> None:
        missing: list[str] = []
        if not self.cloud_account.tenancy_ocid:
            missing.append("tenancy_ocid")
        if not self.cloud_account.user_ocid:
            missing.append("user_ocid")
        if not self.cloud_account.fingerprint:
            missing.append("fingerprint")
        if not self.cloud_account.private_key:
            missing.append("private_key")
        if not (self.cloud_account.region or self.cloud_account.default_region):
            missing.append("region")
        if missing:
            raise OCIConfigurationError(f"Missing OCI configuration fields: {', '.join(missing)}")
