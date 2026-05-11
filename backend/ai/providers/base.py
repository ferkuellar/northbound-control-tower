from abc import ABC, abstractmethod

from ai.schemas import AIProviderStatus


class BaseAIProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    def generate_analysis(self, prompt: str, max_tokens: int, temperature: float) -> str:
        raise NotImplementedError

    @abstractmethod
    def health_check(self) -> AIProviderStatus:
        raise NotImplementedError
