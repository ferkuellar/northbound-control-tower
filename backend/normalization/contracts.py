from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseProviderNormalizer(ABC):
    @abstractmethod
    def normalize_compute(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize_block_storage(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize_object_storage(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize_database(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize_network(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize_identity(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize_monitoring(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def normalize_unknown(self, resource: Any, region: str | None = None) -> dict[str, Any]:
        raise NotImplementedError
