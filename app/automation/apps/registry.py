"""Application Adapter Registry for deterministic adapter lookup and resolution."""

import threading

from app.automation.apps.base import ApplicationAdapter
from app.logging import logger


class ApplicationAdapterRegistry:
    """Registry service mapping app_ids and aliases to registered ApplicationAdapter singletons."""

    def __init__(self) -> None:
        self._adapters: dict[str, ApplicationAdapter] = {}
        self._alias_map: dict[str, str] = {}
        self._lock = threading.Lock()

    def register_adapter(self, adapter: ApplicationAdapter) -> None:
        """Register an application adapter and all its configured search aliases.

        Args:
            adapter: ApplicationAdapter instance to register.

        Raises:
            ValueError: If an adapter with the same app_id is already registered.
        """
        identity = adapter.identity
        app_id = identity.app_id.lower().strip()

        with self._lock:
            if app_id in self._adapters:
                raise ValueError(
                    f"ApplicationAdapter with app_id '{app_id}' is already registered."
                )

            self._adapters[app_id] = adapter
            self._alias_map[app_id] = app_id

            # Register display name and aliases
            if identity.display_name:
                self._alias_map[identity.display_name.lower().strip()] = app_id

            for alias in identity.aliases:
                clean_alias = alias.lower().strip()
                if clean_alias:
                    self._alias_map[clean_alias] = app_id

            logger.info(
                f"ApplicationAdapterRegistry: Registered adapter '{identity.app_id}' "
                f"with {len(identity.aliases)} aliases."
            )

    def get_adapter(self, alias_or_id: str) -> ApplicationAdapter | None:
        """Resolve an adapter by app_id, display name, or alias.

        Args:
            alias_or_id: Search query string.

        Returns:
            Resolved ApplicationAdapter instance or None if not found.
        """
        if not alias_or_id or not isinstance(alias_or_id, str):
            return None

        clean_key = alias_or_id.lower().strip()
        with self._lock:
            app_id = self._alias_map.get(clean_key)
            if app_id and app_id in self._adapters:
                return self._adapters[app_id]
            return None

    def is_adapter_registered(self, alias_or_id: str) -> bool:
        """Check if an adapter exists matching the given app_id or alias."""
        return self.get_adapter(alias_or_id) is not None

    def list_adapters(self) -> list[ApplicationAdapter]:
        """Return list of all currently registered application adapters."""
        with self._lock:
            return list(self._adapters.values())

    def clear(self) -> None:
        """Clear all registered adapters (for testing)."""
        with self._lock:
            self._adapters.clear()
            self._alias_map.clear()
