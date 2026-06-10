"""Tests for security/secrets.py — SecretProvider selection and implementations."""
from __future__ import annotations

import base64
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from security.secrets import (
    EnvSecretProvider,
    OCIVaultSecretProvider,
    SecretProvider,
    get_secret_provider,
)


# ── EnvSecretProvider ─────────────────────────────────────────────────────────

def test_env_provider_reads_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_SECRET_VAR_X", "test-value-abc")
    provider = EnvSecretProvider()
    assert provider.get_secret("TEST_SECRET_VAR_X") == "test-value-abc"


def test_env_provider_returns_none_for_missing_var() -> None:
    provider = EnvSecretProvider()
    assert provider.get_secret("DEFINITELY_NOT_SET_VAR_XYZ_12345") is None


def test_env_provider_is_secret_provider_subclass() -> None:
    assert issubclass(EnvSecretProvider, SecretProvider)


# ── get_secret_provider — development ─────────────────────────────────────────

def test_development_returns_env_provider() -> None:
    with patch("security.secrets.settings") as mock_settings:
        mock_settings.app_env = "development"
        provider = get_secret_provider()
    assert isinstance(provider, EnvSecretProvider)


def test_test_env_returns_env_provider() -> None:
    with patch("security.secrets.settings") as mock_settings:
        mock_settings.app_env = "test"
        provider = get_secret_provider()
    assert isinstance(provider, EnvSecretProvider)


def test_local_env_returns_env_provider() -> None:
    with patch("security.secrets.settings") as mock_settings:
        mock_settings.app_env = "local"
        provider = get_secret_provider()
    assert isinstance(provider, EnvSecretProvider)


# ── get_secret_provider — production without cloud provider ───────────────────

def test_production_without_vault_id_raises() -> None:
    with patch("security.secrets.settings") as mock_settings:
        mock_settings.app_env = "production"
        mock_settings.oci_vault_id = None
        with pytest.raises(RuntimeError, match="OCI_VAULT_ID"):
            get_secret_provider()


def test_production_without_vault_id_error_mentions_cloud_provider() -> None:
    with patch("security.secrets.settings") as mock_settings:
        mock_settings.app_env = "production"
        mock_settings.oci_vault_id = None
        with pytest.raises(RuntimeError, match="cloud secret provider"):
            get_secret_provider()


# ── get_secret_provider — production with OCI Vault ──────────────────────────

def test_production_with_vault_id_returns_oci_provider() -> None:
    mock_oci = MagicMock()
    mock_oci.config.from_file.return_value = {"region": "us-ashburn-1"}

    with patch("security.secrets.settings") as mock_settings, \
         patch.dict("sys.modules", {"oci": mock_oci,
                                    "oci.config": mock_oci.config,
                                    "oci.secrets": mock_oci.secrets,
                                    "oci.vault": mock_oci.vault,
                                    "oci.exceptions": mock_oci.exceptions}):
        mock_settings.app_env = "production"
        mock_settings.oci_vault_id = "ocid1.vault.oc1.iad.test.aaaaaa"
        mock_settings.oci_default_region = "us-ashburn-1"
        provider = get_secret_provider()

    assert isinstance(provider, OCIVaultSecretProvider)


# ── OCIVaultSecretProvider — constructor ──────────────────────────────────────

def _make_oci_provider(vault_id: str = "ocid1.vault.test", region: str = "us-ashburn-1") -> tuple[OCIVaultSecretProvider, MagicMock]:
    mock_oci = MagicMock()
    mock_oci.config.from_file.return_value = {"region": region}

    with patch.dict("sys.modules", {"oci": mock_oci,
                                    "oci.config": mock_oci.config,
                                    "oci.secrets": mock_oci.secrets,
                                    "oci.vault": mock_oci.vault,
                                    "oci.exceptions": mock_oci.exceptions}):
        provider = OCIVaultSecretProvider(vault_id=vault_id, region=region)

    provider._oci = mock_oci
    provider._secrets_client = mock_oci.secrets.SecretsClient.return_value
    provider._vaults_client = mock_oci.vault.VaultsClient.return_value
    return provider, mock_oci


def test_oci_provider_is_secret_provider_subclass() -> None:
    assert issubclass(OCIVaultSecretProvider, SecretProvider)


def test_oci_provider_sets_region_on_config() -> None:
    mock_oci = MagicMock()
    captured_config: dict = {}

    def capture_config(config):
        captured_config.update(config)
        return MagicMock()

    mock_oci.config.from_file.return_value = {"region": "us-ashburn-1"}
    mock_oci.secrets.SecretsClient.side_effect = capture_config

    with patch.dict("sys.modules", {"oci": mock_oci,
                                    "oci.config": mock_oci.config,
                                    "oci.secrets": mock_oci.secrets,
                                    "oci.vault": mock_oci.vault,
                                    "oci.exceptions": mock_oci.exceptions}):
        OCIVaultSecretProvider(vault_id="ocid1.vault.test", region="ap-tokyo-1")

    assert captured_config.get("region") == "ap-tokyo-1"


def test_oci_provider_raises_if_oci_not_installed() -> None:
    import sys
    saved = sys.modules.pop("oci", None)
    try:
        with patch.dict("sys.modules", {"oci": None}):  # type: ignore[dict-item]
            with pytest.raises((RuntimeError, ImportError)):
                OCIVaultSecretProvider(vault_id="ocid1.vault.test", region="us-ashburn-1")
    finally:
        if saved is not None:
            sys.modules["oci"] = saved


# ── OCIVaultSecretProvider.get_secret — happy path ───────────────────────────

def test_oci_get_secret_returns_decoded_value() -> None:
    provider, mock_oci = _make_oci_provider()

    vault_data = SimpleNamespace(compartment_id="ocid1.compartment.test")
    provider._vaults_client.get_vault.return_value = SimpleNamespace(data=vault_data)

    secret_summary = SimpleNamespace(id="ocid1.secret.test")
    provider._vaults_client.list_secrets.return_value = SimpleNamespace(data=[secret_summary])

    encoded = base64.b64encode(b"super-secret-value").decode("utf-8")
    bundle_content = SimpleNamespace(content=encoded)
    bundle = SimpleNamespace(secret_bundle_content=bundle_content)
    provider._secrets_client.get_secret_bundle.return_value = SimpleNamespace(data=bundle)

    result = provider.get_secret("MY_SECRET")
    assert result == "super-secret-value"


def test_oci_get_secret_returns_none_when_not_found() -> None:
    provider, mock_oci = _make_oci_provider()

    vault_data = SimpleNamespace(compartment_id="ocid1.compartment.test")
    provider._vaults_client.get_vault.return_value = SimpleNamespace(data=vault_data)
    provider._vaults_client.list_secrets.return_value = SimpleNamespace(data=[])

    result = provider.get_secret("NONEXISTENT_SECRET")
    assert result is None


def test_oci_get_secret_returns_none_on_404() -> None:
    provider, mock_oci = _make_oci_provider()

    vault_data = SimpleNamespace(compartment_id="ocid1.compartment.test")
    provider._vaults_client.get_vault.return_value = SimpleNamespace(data=vault_data)

    service_error = MagicMock()
    service_error.status = 404
    mock_oci.exceptions.ServiceError = type("ServiceError", (Exception,), {})
    exc_instance = mock_oci.exceptions.ServiceError("not found")
    exc_instance.status = 404
    provider._vaults_client.list_secrets.side_effect = exc_instance

    provider._oci.exceptions.ServiceError = mock_oci.exceptions.ServiceError

    result = provider.get_secret("MISSING_SECRET")
    assert result is None


def test_oci_get_secret_does_not_log_secret_value(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    provider, mock_oci = _make_oci_provider()

    vault_data = SimpleNamespace(compartment_id="ocid1.compartment.test")
    provider._vaults_client.get_vault.return_value = SimpleNamespace(data=vault_data)

    secret_summary = SimpleNamespace(id="ocid1.secret.test")
    provider._vaults_client.list_secrets.return_value = SimpleNamespace(data=[secret_summary])

    sensitive_value = "TOP-SECRET-PASSWORD-XYZ"
    encoded = base64.b64encode(sensitive_value.encode()).decode("utf-8")
    bundle_content = SimpleNamespace(content=encoded)
    bundle = SimpleNamespace(secret_bundle_content=bundle_content)
    provider._secrets_client.get_secret_bundle.return_value = SimpleNamespace(data=bundle)

    with caplog.at_level(logging.DEBUG):
        provider.get_secret("MY_SECRET")

    assert sensitive_value not in caplog.text


# ── _validate_production_secrets — OCI Vault guard ───────────────────────────

def test_production_validate_raises_without_oci_vault_id() -> None:
    from api.main import _validate_production_secrets

    with patch("api.main.settings") as mock:
        mock.app_env = "production"
        mock.jwt_secret_key = "a-very-long-random-secret-not-the-default"
        mock.credential_encryption_key = "a-valid-fernet-key"
        mock.database_url = "postgresql+psycopg://nct:str0ng-pass@postgres:5432/nct"
        mock.oci_vault_id = None
        with pytest.raises(RuntimeError, match="OCI_VAULT_ID"):
            _validate_production_secrets()


def test_production_validate_passes_with_oci_vault_id() -> None:
    from api.main import _validate_production_secrets

    with patch("api.main.settings") as mock:
        mock.app_env = "production"
        mock.jwt_secret_key = "a-very-long-random-secret-not-the-default"
        mock.credential_encryption_key = "a-valid-fernet-key"
        mock.database_url = "postgresql+psycopg://nct:str0ng-pass@postgres:5432/nct"
        mock.oci_vault_id = "ocid1.vault.oc1.iad.test.aaaaaa"
        mock.backend_cors_origins_raw = "https://app.northbound.io"
        _validate_production_secrets()  # must not raise


# ── .env.example has no real secrets ─────────────────────────────────────────

def test_env_example_oci_vault_id_is_empty() -> None:
    import pathlib

    candidates = [
        pathlib.Path(__file__).parents[2] / ".env.example",
        pathlib.Path(__file__).parents[1].parent / ".env.example",
    ]
    env_example = next((p for p in candidates if p.exists()), None)
    if env_example is None:
        pytest.skip(".env.example not available in this environment")

    content = env_example.read_text(encoding="utf-8")
    assert "OCI_VAULT_ID=" in content, ".env.example must document OCI_VAULT_ID"
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("OCI_VAULT_ID="):
            value = stripped[len("OCI_VAULT_ID="):]
            assert not value.startswith("ocid1.vault.oc1"), (
                ".env.example must not contain a real OCI Vault OCID"
            )
