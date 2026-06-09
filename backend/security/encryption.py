from __future__ import annotations

from cryptography.fernet import Fernet

from core.config import settings


def _fernet() -> Fernet:
    key = settings.credential_encryption_key
    if not key:
        raise RuntimeError(
            "CREDENTIAL_ENCRYPTION_KEY is not configured. "
            "Set the environment variable to enable credential encryption."
        )
    return Fernet(key.encode())


def encrypt_credential(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt_credential(value: str | None) -> str | None:
    if not value:
        return value
    return _fernet().decrypt(value.encode()).decode()
