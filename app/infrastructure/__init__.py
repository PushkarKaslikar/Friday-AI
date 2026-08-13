"""Infrastructure layer providing low-level system and I/O implementations."""

from abc import ABC, abstractmethod


class BaseInfrastructureProvider(ABC):
    """Abstract base class for external system and infrastructure providers."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if infrastructure component is available on current system."""


__all__ = ["BaseInfrastructureProvider"]
