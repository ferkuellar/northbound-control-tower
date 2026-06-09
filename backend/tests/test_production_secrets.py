from unittest.mock import patch

import pytest

from api.main import _UNSAFE_JWT_SECRET, _validate_production_secrets


def test_production_with_default_secret_raises() -> None:
    with patch("api.main.settings") as mock:
        mock.app_env = "production"
        mock.jwt_secret_key = _UNSAFE_JWT_SECRET
        with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
            _validate_production_secrets()


def test_production_with_strong_secret_passes() -> None:
    with patch("api.main.settings") as mock:
        mock.app_env = "production"
        mock.jwt_secret_key = "a-very-long-random-secret-not-the-default"
        mock.credential_encryption_key = "a-valid-fernet-key"
        _validate_production_secrets()  # must not raise


def test_production_without_credential_key_raises() -> None:
    with patch("api.main.settings") as mock:
        mock.app_env = "production"
        mock.jwt_secret_key = "a-very-long-random-secret-not-the-default"
        mock.credential_encryption_key = None
        with pytest.raises(RuntimeError, match="CREDENTIAL_ENCRYPTION_KEY"):
            _validate_production_secrets()


def test_development_with_default_secret_passes() -> None:
    with patch("api.main.settings") as mock:
        mock.app_env = "development"
        mock.jwt_secret_key = _UNSAFE_JWT_SECRET
        _validate_production_secrets()  # must not raise


# ── Claude model default ──────────────────────────────────────────────────────

def test_claude_model_default_is_current() -> None:
    from core.config import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.claude_model == "claude-sonnet-4-6"


def test_claude_model_respects_env_override(monkeypatch) -> None:
    monkeypatch.setenv("CLAUDE_MODEL", "claude-opus-4-8")
    from core.config import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.claude_model == "claude-opus-4-8"


def test_claude_model_old_default_not_hardcoded() -> None:
    import inspect
    import core.config as config_module

    source = inspect.getsource(config_module)
    assert "claude-3-5-sonnet-latest" not in source
