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
        _validate_production_secrets()  # must not raise


def test_development_with_default_secret_passes() -> None:
    with patch("api.main.settings") as mock:
        mock.app_env = "development"
        mock.jwt_secret_key = _UNSAFE_JWT_SECRET
        _validate_production_secrets()  # must not raise
