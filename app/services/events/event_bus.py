"""Centralized thread-safe Event Bus for pub/sub decoupled event delivery."""

import threading
from collections import defaultdict
from collections.abc import Callable
from typing import Optional

from app.logging import logger
from app.services.events.event_models import Event

EventHandler = Callable[[Event], None]


class EventBus:
    """Centralized thread-safe Event Bus delivering typed events to subscribers."""

    _instance: Optional["EventBus"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._lock = threading.RLock()
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)
        self._initialized = True

    def subscribe(
        self,
        event_type: str | type[Event],
        handler: EventHandler,
    ) -> None:
        """Subscribe handler function to an event type name, Event class, or wildcard ('*').

        Args:
            event_type: Event class, event type string, or '*' for all events.
            handler: Callable taking an Event instance.
        """
        key = event_type if isinstance(event_type, str) else event_type.__name__
        with self._lock:
            if handler not in self._subscribers[key]:
                self._subscribers[key].append(handler)
                logger.debug(f"EventBus: Registered subscriber for '{key}'.")

    def unsubscribe(
        self,
        event_type: str | type[Event],
        handler: EventHandler,
    ) -> bool:
        """Unsubscribe handler function from an event type.

        Returns:
            bool: True if handler was found and removed.
        """
        key = event_type if isinstance(event_type, str) else event_type.__name__
        with self._lock:
            if key in self._subscribers and handler in self._subscribers[key]:
                self._subscribers[key].remove(handler)
                logger.debug(f"EventBus: Unsubscribed handler from '{key}'.")
                return True
        return False

    def publish(self, event: Event) -> None:
        """Publish event to all registered subscribers synchronously with error isolation.

        Args:
            event: Event instance to publish.
        """
        event_key = event.event_type

        with self._lock:
            handlers = list(self._subscribers.get(event_key, []))
            wildcard_handlers = list(self._subscribers.get("*", []))

        all_handlers = handlers + wildcard_handlers

        for handler in all_handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"EventBus: Exception in handler '{handler.__name__}' for event '{event_key}': {exc}"
                )

    def clear(self) -> None:
        """Clear all event subscribers."""
        with self._lock:
            self._subscribers.clear()
