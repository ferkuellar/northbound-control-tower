from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

from core.database import SessionLocal
from models.cloud_account import CloudAccount
from models.tenant import Tenant
from security.encryption import decrypt_credential, encrypt_credential


_TEST_KEY = Fernet.generate_key().decode()
_MOCK_SETTINGS = SimpleNamespace(credential_encryption_key=_TEST_KEY)


# ---------------------------------------------------------------------------
# Unit: encrypt / decrypt functions
# ---------------------------------------------------------------------------

def test_encrypt_returns_different_value(monkeypatch):
    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    result = encrypt_credential("my-secret")
    assert result != "my-secret"
    assert result is not None


def test_encrypted_value_is_fernet_token(monkeypatch):
    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    result = encrypt_credential("my-secret")
    assert result.startswith("gAAAA")


def test_decrypt_recovers_original(monkeypatch):
    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    encrypted = encrypt_credential("my-secret")
    assert decrypt_credential(encrypted) == "my-secret"


def test_encrypt_none_returns_none(monkeypatch):
    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    assert encrypt_credential(None) is None


def test_encrypt_empty_string_returns_none(monkeypatch):
    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    assert encrypt_credential("") is None


def test_decrypt_none_returns_none(monkeypatch):
    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    assert decrypt_credential(None) is None


def test_encrypt_raises_without_key():
    from types import SimpleNamespace
    import security.encryption as enc_module
    original = enc_module.settings
    enc_module.settings = SimpleNamespace(credential_encryption_key=None)
    try:
        with pytest.raises(RuntimeError, match="CREDENTIAL_ENCRYPTION_KEY"):
            encrypt_credential("some-value")
    finally:
        enc_module.settings = original


# ---------------------------------------------------------------------------
# Persistence: values stored encrypted
# ---------------------------------------------------------------------------

def _seed_tenant(db) -> "Tenant":
    suffix = uuid.uuid4().hex
    tenant = Tenant(name=f"Enc Tenant {suffix}", slug=f"enc-{suffix}", status="active")
    db.add(tenant)
    db.flush()
    return tenant


def test_secret_access_key_encrypted_at_insert(monkeypatch):
    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    monkeypatch.setattr("models.cloud_account.settings", _MOCK_SETTINGS)

    db = SessionLocal()
    try:
        tenant = _seed_tenant(db)
        account = CloudAccount(
            tenant_id=tenant.id,
            provider="aws",
            name="Enc AWS",
            auth_type="access_keys",
            access_key_id="AKIATEST",
            secret_access_key="plaintext-secret",
            default_region="us-east-1",
            is_active=True,
        )
        db.add(account)
        db.commit()
        db.refresh(account)

        stored = account.secret_access_key
        assert stored != "plaintext-secret"
        assert stored.startswith("gAAAA")
        assert decrypt_credential(stored) == "plaintext-secret"
    finally:
        db.close()


def test_private_key_encrypted_at_insert(monkeypatch):
    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    monkeypatch.setattr("models.cloud_account.settings", _MOCK_SETTINGS)

    db = SessionLocal()
    try:
        tenant = _seed_tenant(db)
        account = CloudAccount(
            tenant_id=tenant.id,
            provider="oci",
            name="Enc OCI",
            auth_type="oci_api_key",
            default_region="us-ashburn-1",
            private_key="-----BEGIN PRIVATE KEY-----\nABCD\n-----END PRIVATE KEY-----",
            private_key_passphrase="my-passphrase",
            is_active=True,
        )
        db.add(account)
        db.commit()
        db.refresh(account)

        assert account.private_key.startswith("gAAAA")
        assert account.private_key_passphrase.startswith("gAAAA")
        assert decrypt_credential(account.private_key).startswith("-----BEGIN PRIVATE KEY-----")
        assert decrypt_credential(account.private_key_passphrase) == "my-passphrase"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# No double encryption on update
# ---------------------------------------------------------------------------

def test_update_does_not_double_encrypt(monkeypatch):
    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    monkeypatch.setattr("models.cloud_account.settings", _MOCK_SETTINGS)

    db = SessionLocal()
    try:
        tenant = _seed_tenant(db)
        account = CloudAccount(
            tenant_id=tenant.id,
            provider="aws",
            name="NDE AWS",
            auth_type="access_keys",
            access_key_id="AKIATEST",
            secret_access_key="plaintext-secret",
            default_region="us-east-1",
            is_active=True,
        )
        db.add(account)
        db.commit()
        db.refresh(account)

        first_encrypted = account.secret_access_key
        assert first_encrypted.startswith("gAAAA")

        account.name = "NDE AWS Updated"
        db.commit()
        db.refresh(account)

        assert account.secret_access_key == first_encrypted
        assert decrypt_credential(account.secret_access_key) == "plaintext-secret"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Session consumption: decrypt before use
# ---------------------------------------------------------------------------

def test_aws_session_factory_decrypts_secret_access_key(monkeypatch):
    import boto3
    from collectors.aws.session import AWSSessionFactory

    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    encrypted = encrypt_credential("REAL-SECRET-KEY")

    captured: dict = {}

    def fake_session(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace()

    monkeypatch.setattr(boto3, "Session", fake_session)

    account = SimpleNamespace(
        auth_type="access_keys",
        access_key_id="AKIATEST",
        secret_access_key=encrypted,
        default_region="us-east-1",
    )
    AWSSessionFactory(account, timeout_seconds=30).create_session()

    assert captured["aws_secret_access_key"] == "REAL-SECRET-KEY"


def test_oci_session_factory_decrypts_private_key(monkeypatch):
    import oci.config as oci_config_module
    from collectors.oci.session import OCISessionFactory

    monkeypatch.setattr("security.encryption.settings", _MOCK_SETTINGS)
    encrypted_key = encrypt_credential("-----BEGIN PRIVATE KEY-----\nXYZ\n-----END PRIVATE KEY-----")
    encrypted_pass = encrypt_credential("secret-passphrase")

    validated: dict = {}

    def fake_validate(config):
        validated.update(config)

    monkeypatch.setattr(oci_config_module, "validate_config", fake_validate)

    account = SimpleNamespace(
        auth_type="oci_api_key",
        tenancy_ocid="ocid1.tenancy",
        user_ocid="ocid1.user",
        fingerprint="aa:bb:cc",
        private_key=encrypted_key,
        private_key_passphrase=encrypted_pass,
        region="us-ashburn-1",
        default_region="us-ashburn-1",
        compartment_ocid=None,
    )
    OCISessionFactory(account).create_config()

    assert validated["key_content"].startswith("-----BEGIN PRIVATE KEY-----")
    assert validated["pass_phrase"] == "secret-passphrase"


# ---------------------------------------------------------------------------
# API response does not expose credentials
# ---------------------------------------------------------------------------

def test_cloud_account_read_schema_excludes_credentials():
    from api.schemas.inventory import CloudAccountRead
    fields = CloudAccountRead.model_fields
    assert "secret_access_key" not in fields
    assert "private_key" not in fields
    assert "private_key_passphrase" not in fields
    assert "access_key_id" not in fields
