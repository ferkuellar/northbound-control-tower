import anthropic

from ai.enums import AIProvider
from ai.providers.base import BaseAIProvider
from ai.schemas import AIProviderStatus
from core.config import settings


class ClaudeProvider(BaseAIProvider):
    provider_name = AIProvider.CLAUDE.value

    def __init__(self) -> None:
        self.model_name = settings.claude_model
        self.api_key = settings.anthropic_api_key

    def health_check(self) -> AIProviderStatus:
        configured = bool(self.api_key)
        return AIProviderStatus(
            provider=AIProvider.CLAUDE,
            configured=configured,
            enabled=configured,
            model_name=self.model_name,
            base_url=None,
            message="configured" if configured else "provider key is not configured",
        )

    def generate_analysis(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not self.api_key:
            raise ValueError("provider key is not configured")
        client = anthropic.Anthropic(api_key=self.api_key, timeout=settings.ai_request_timeout_seconds)
        response = client.messages.create(
            model=self.model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in response.content if getattr(block, "type", None) == "text"]
        return "\n".join(parts)
