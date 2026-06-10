from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.config import settings


class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self, name: str) -> str | None:
        raise NotImplementedError


class EnvSecretProvider(SecretProvider):
    def get_secret(self, name: str) -> str | None:
        return os.getenv(name)


class OCIVaultSecretProvider(SecretProvider):
    """Retrieve secrets from OCI Vault.

    Requires the OCI SDK (oci package) and a valid OCI configuration at
    ~/.oci/config or via instance principal / resource principal auth.

    Secret retrieval flow:
      1. Get vault to resolve the compartment OCID.
      2. List secrets in that vault by name.
      3. Fetch the current secret bundle.
      4. Base64-decode and return the plaintext value.

    Secret values are never logged.
    """

    def __init__(self, vault_id: str, region: str) -> None:
        try:
            import oci as _oci
        except ImportError as exc:
            raise RuntimeError(
                "OCI SDK is required for OCIVaultSecretProvider. "
                "Install the oci package or disable OCI Vault provider."
            ) from exc

        self._oci = _oci
        self._vault_id = vault_id
        self._region = region

        oci_config = _oci.config.from_file()
        oci_config["region"] = region
        self._secrets_client = _oci.secrets.SecretsClient(config=oci_config)
        self._vaults_client = _oci.vault.VaultsClient(config=oci_config)

    def get_secret(self, name: str) -> str | None:
        try:
            vault = self._vaults_client.get_vault(self._vault_id).data
            compartment_id = vault.compartment_id

            results = self._vaults_client.list_secrets(
                compartment_id,
                name=name,
                vault_id=self._vault_id,
            ).data

            if not results:
                return None

            bundle = self._secrets_client.get_secret_bundle(results[0].id).data
            encoded = bundle.secret_bundle_content.content
            return base64.b64decode(encoded).decode("utf-8")
        except self._oci.exceptions.ServiceError as exc:
            if exc.status == 404:
                return None
            raise


@dataclass(frozen=True)
class SecretReference:
    provider: str
    name: str


def get_secret_provider() -> SecretProvider:
    """Return the appropriate SecretProvider for the current environment.

    Development/test: EnvSecretProvider (reads from process environment / .env).
    Production with OCI_VAULT_ID: OCIVaultSecretProvider.
    Production without OCI_VAULT_ID: raises RuntimeError — production must not
    fall back to .env as a secret source.
    """
    if settings.app_env == "production":
        if settings.oci_vault_id:
            return OCIVaultSecretProvider(
                vault_id=settings.oci_vault_id,
                region=settings.oci_default_region,
            )
        raise RuntimeError(
            "Production secrets must come from a cloud secret provider. "
            "Set OCI_VAULT_ID or configure an approved production secret provider."
        )
    return EnvSecretProvider()


def get_secret(name: str) -> str | None:
    return get_secret_provider().get_secret(name)


def configured_ai_secret(provider: str) -> SecretReference | None:
    mapping = {
        "deepseek": "DEEPSEEK_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    env_name = mapping.get(provider)
    if not env_name:
        return None
    value = get_secret(env_name)
    return SecretReference(provider="env", name=env_name) if value else None


def local_secret_storage_notice() -> dict[str, str]:
    return {
        "mode": "local_env",
        "environment": settings.app_env,
        "technical_debt": "Cloud account credentials stored in the database are tolerated only for local Phase 12 development.",
    }
