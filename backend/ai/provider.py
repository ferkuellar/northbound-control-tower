from dataclasses import dataclass

from ai.enums import AIProvider
from ai.errors import AIProviderConfigurationError
from ai.providers import BaseAIProvider, ClaudeProvider, DeepSeekProvider, OpenAIProvider
from core.config import settings


@dataclass(frozen=True)
class AIProviderConfig:
    provider: AIProvider
    api_key_configured: bool
    base_url: str | None
    model: str | None


def _coerce_provider(provider: str | AIProvider | None) -> AIProvider:
    value = (provider or settings.ai_provider).value if isinstance(provider, AIProvider) else provider or settings.ai_provider
    try:
        return AIProvider(str(value).lower())
    except ValueError as exc:
        raise AIProviderConfigurationError(f"Unsupported AI provider: {value}") from exc


def get_ai_provider_config(provider: str | AIProvider | None = None) -> AIProviderConfig:
    selected = _coerce_provider(provider)
    if selected == AIProvider.DEEPSEEK:
        return AIProviderConfig(selected, bool(settings.deepseek_api_key), settings.deepseek_base_url, settings.deepseek_model)
    if selected == AIProvider.CLAUDE:
        return AIProviderConfig(selected, bool(settings.anthropic_api_key), None, settings.claude_model)
    if selected == AIProvider.OPENAI:
        return AIProviderConfig(selected, bool(settings.openai_api_key or settings.ai_api_key), None, settings.openai_model)
    return AIProviderConfig(AIProvider.NONE, True, None, None)


def validate_ai_provider_config(provider: str | AIProvider | None = None) -> dict[str, bool | str | None]:
    config = get_ai_provider_config(provider)
    return {
        "provider": config.provider.value,
        "configured": config.provider == AIProvider.NONE or config.api_key_configured,
        "base_url": config.base_url,
        "model": config.model,
    }


def get_ai_provider(provider: str | AIProvider | None = None) -> BaseAIProvider:
    selected = _coerce_provider(provider)
    if selected == AIProvider.NONE:
        raise AIProviderConfigurationError("AI provider is disabled. Configure AI_PROVIDER or pass a provider.")
    if selected == AIProvider.DEEPSEEK:
        instance: BaseAIProvider = DeepSeekProvider()
    elif selected == AIProvider.CLAUDE:
        instance = ClaudeProvider()
    elif selected == AIProvider.OPENAI:
        instance = OpenAIProvider()
    else:
        raise AIProviderConfigurationError(f"Unsupported AI provider: {selected}")

    status = instance.health_check()
    if not status.configured:
        raise AIProviderConfigurationError(status.message)
    return instance


def get_ai_client() -> BaseAIProvider | None:
    if _coerce_provider(None) == AIProvider.NONE:
        return None
    return get_ai_provider()
