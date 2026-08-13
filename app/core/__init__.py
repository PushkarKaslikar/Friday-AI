"""Core Domain layer containing domain abstractions and entities."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class BaseDomainModel(ABC):
    """Abstract base class for all domain entities."""


class BaseRepository(ABC, Generic[T]):
    """Generic repository interface definition for domain entities."""

    @abstractmethod
    def get_by_id(self, entity_id: str) -> T | None:
        """Fetch entity by unique identifier."""
        ...


__all__ = ["BaseDomainModel", "BaseRepository"]
