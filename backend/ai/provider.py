from dataclasses import dataclass
from enum import StrEnum

from openai import OpenAI

from core.config import settings


class AIProvider(StrEnum):
    NONE = "none"
    OPENAI = "openai"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"


@dataclass(frozen=True)
class AIProviderConfig:
    provider: AIProvider
    api_key_configured: bool
    base_url: str | None
    model: str | None


def get_ai_provider_config() -> AIProviderConfig:
    provider = AIProvider(settings.ai_provider.lower())
    if provider == AIProvider.DEEPSEEK:
        return AIProviderConfig(
            provider=provider,
            api_key_configured=bool(settings.deepseek_api_key),
            base_url=settings.deepseek_base_url,
            model=settings.deepseek_model,
        )
    return AIProviderConfig(
        provider=provider,
        api_key_configured=bool(settings.ai_api_key),
        base_url=settings.ai_base_url,
        model=settings.ai_model,
    )


def validate_ai_provider_config() -> dict[str, bool | str | None]:
    config = get_ai_provider_config()
    return {
        "provider": config.provider.value,
        "configured": config.provider == AIProvider.NONE or config.api_key_configured,
        "base_url": config.base_url,
        "model": config.model,
    }


def get_ai_client() -> OpenAI | None:
    config = get_ai_provider_config()
    if config.provider == AIProvider.NONE:
        return None
    if not config.api_key_configured:
        raise ValueError("AI provider API key is not configured")
    if config.provider == AIProvider.CLAUDE:
        raise ValueError("Claude client is not implemented in this phase")
    api_key = settings.deepseek_api_key if config.provider == AIProvider.DEEPSEEK else settings.ai_api_key
    return OpenAI(api_key=api_key, base_url=config.base_url)
