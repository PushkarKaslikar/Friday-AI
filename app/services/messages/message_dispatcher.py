"""Internal Message Dispatcher for module message routing and priority handling."""

import threading
from collections.abc import Callable
from typing import Any, Optional

from app.logging import logger

MessageHandler = Callable[[str, dict[str, Any]], None]


class MessageDispatcher:
    """Internal message dispatcher routing decoupled payload messages across module targets."""

    _instance: Optional["MessageDispatcher"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._lock = threading.RLock()
        self._handlers: dict[str, list[MessageHandler]] = {}
        self._initialized = True

    def register_route(self, route_key: str, handler: MessageHandler) -> None:
        """Register a handler function for a specific message route key."""
        with self._lock:
            if route_key not in self._handlers:
                self._handlers[route_key] = []
            if handler not in self._handlers[route_key]:
                self._handlers[route_key].append(handler)
                logger.debug(
                    f"MessageDispatcher: Registered handler for route '{route_key}'."
                )

    def unregister_route(self, route_key: str, handler: MessageHandler) -> bool:
        """Unregister a handler from a route key."""
        with self._lock:
            if route_key in self._handlers and handler in self._handlers[route_key]:
                self._handlers[route_key].remove(handler)
                logger.debug(
                    f"MessageDispatcher: Unregistered handler for route '{route_key}'."
                )
                return True
        return False

    def dispatch(self, route_key: str, payload: dict[str, Any] | None = None) -> int:
        """Dispatch message payload to all registered route handlers.

        Args:
            route_key: Target routing identifier.
            payload: Optional dictionary payload.

        Returns:
            int: Count of handlers invoked.
        """
        payload_data = payload or {}
        with self._lock:
            handlers = list(self._handlers.get(route_key, []))

        invoked_count = 0
        for handler in handlers:
            try:
                handler(route_key, payload_data)
                invoked_count += 1
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"MessageDispatcher: Error executing handler for route '{route_key}': {exc}"
                )

        return invoked_count

    def clear(self) -> None:
        """Clear all registered routes."""
        with self._lock:
            self._handlers.clear()
