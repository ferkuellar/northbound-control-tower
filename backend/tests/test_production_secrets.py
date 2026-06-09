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


# ── AI token and timeout defaults ─────────────────────────────────────────────

def test_ai_max_tokens_default_is_4000() -> None:
    from core.config import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.ai_max_tokens == 4000


def test_ai_max_tokens_respects_env_override(monkeypatch) -> None:
    monkeypatch.setenv("AI_MAX_TOKENS", "2500")
    from core.config import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.ai_max_tokens == 2500


def test_ai_request_timeout_default_is_90() -> None:
    from core.config import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.ai_request_timeout_seconds == 90


def test_ai_provider_default_is_none() -> None:
    from core.config import Settings

    s = Settings(_env_file=None)  # type: ignore[call-arg]
    assert s.ai_provider == "none"


def test_env_example_contains_no_real_api_key() -> None:
    import pathlib
    import re

    # .env.example is at the repo root, one level above the backend dir.
    # In Docker the backend is mounted at /app; the repo root is not mounted,
    # so skip gracefully when the file is absent (e.g. in CI containers).
    candidates = [
        pathlib.Path(__file__).parents[2] / ".env.example",   # repo root on host
        pathlib.Path(__file__).parents[1].parent / ".env.example",
    ]
    env_example = next((p for p in candidates if p.exists()), None)
    if env_example is None:
        import pytest
        pytest.skip(".env.example not available in this environment")

    content = env_example.read_text(encoding="utf-8")
    real_key_pattern = re.compile(r"ANTHROPIC_API_KEY=sk-ant-api03-[A-Za-z0-9_\-]{20,}")
    assert not real_key_pattern.search(content), ".env.example must not contain a real Anthropic API key"
