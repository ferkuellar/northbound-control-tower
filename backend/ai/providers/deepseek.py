from openai import OpenAI

from ai.enums import AIProvider
from ai.providers.base import BaseAIProvider
from ai.schemas import AIProviderStatus
from core.config import settings


class DeepSeekProvider(BaseAIProvider):
    provider_name = AIProvider.DEEPSEEK.value

    def __init__(self) -> None:
        self.model_name = settings.deepseek_model
        self.api_key = settings.deepseek_api_key
        self.base_url = settings.deepseek_base_url

    def health_check(self) -> AIProviderStatus:
        configured = bool(self.api_key)
        return AIProviderStatus(
            provider=AIProvider.DEEPSEEK,
            configured=configured,
            enabled=configured,
            model_name=self.model_name,
            base_url=self.base_url,
            message="configured" if configured else "provider key is not configured",
        )

    def generate_analysis(self, prompt: str, max_tokens: int, temperature: float) -> str:
        if not self.api_key:
            raise ValueError("provider key is not configured")
        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=settings.ai_request_timeout_seconds)
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""
