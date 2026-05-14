from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass

from core.config import settings


class SecretProvider(ABC):
    @abstractmethod
    def get_secret(self, name: str) -> str | None:
        raise NotImplementedError


class EnvSecretProvider(SecretProvider):
    def get_secret(self, name: str) -> str | None:
        return os.getenv(name)


@dataclass(frozen=True)
class SecretReference:
    provider: str
    name: str


def get_secret_provider() -> SecretProvider:
    return EnvSecretProvider()


def get_secret(name: str) -> str | None:
    return get_secret_provider().get_secret(name)


def configured_ai_secret(provider: str) -> SecretReference | None:
    mapping = {
        "deepseek": "DEEPSEEK_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
    }
    env_name = mapping.get(provider)
    if not env_name:
        return None
    value = get_secret(env_name)
    return SecretReference(provider="env", name=env_name) if value else None


def local_secret_storage_notice() -> dict[str, str]:
    return {
        "mode": "local_env",
        "environment": settings.app_env,
        "technical_debt": "Cloud account credentials stored in the database are tolerated only for local Phase 12 development.",
    }
