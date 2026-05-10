from abc import ABC, abstractmethod

from models.normalized_resource import NormalizedResource


class InventoryCollector(ABC):
    provider: str

    @abstractmethod
    def collect(self) -> list[NormalizedResource]:
        """Collect and return cloud-agnostic resources."""
