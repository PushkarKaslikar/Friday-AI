"""Events package providing application-wide signal and event bus abstractions."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any


class EventBus(ABC):
    """Abstract Event Bus interface for decoupled publish-subscribe messaging."""

    @abstractmethod
    def subscribe(self, event_type: str, handler: Callable[[Any], None]) -> None:
        """Subscribe handler function to event_type."""

    @abstractmethod
    def publish(self, event_type: str, data: Any = None) -> None:
        """Publish event to all registered handlers."""


__all__ = ["EventBus"]
