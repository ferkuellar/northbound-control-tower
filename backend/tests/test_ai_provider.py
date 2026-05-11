from ai.provider import AIProvider, get_ai_provider_config, validate_ai_provider_config
from core.config import get_settings


def test_default_ai_provider_is_none() -> None:
    get_settings.cache_clear()

    config = get_ai_provider_config()

    assert config.provider == AIProvider.NONE
    assert validate_ai_provider_config()["configured"] is True
