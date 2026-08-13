"""Plugin Registry tracking installed, loaded, active, and disabled plugins."""

import threading
from typing import Any, Optional

from app.logging import logger
from app.plugins.base.plugin_interface import BasePlugin


class PluginRegistry:
    """Centralized registry for installed, active, and disabled plugins."""

    _instance: Optional["PluginRegistry"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._lock = threading.RLock()
        self._plugins: dict[str, BasePlugin] = {}
        self._disabled_plugins: set[str] = set()
        self._initialized = True
        logger.info("PluginRegistry initialized.")

    def register(self, plugin: BasePlugin) -> bool:
        """Register a validated plugin instance.

        Args:
            plugin: BasePlugin instance.

        Returns:
            bool: True if registered successfully.
        """
        pid = plugin.plugin_id
        with self._lock:
            if pid in self._plugins:
                logger.warning(f"PluginRegistry: Plugin '{pid}' is already registered.")
                return False

            self._plugins[pid] = plugin
            logger.info(
                f"PluginRegistry: Registered plugin '{plugin.metadata.name}' (v{plugin.metadata.version})."
            )
            return True

    def unregister(self, plugin_id: str) -> bool:
        """Unregister a plugin by ID."""
        with self._lock:
            plugin = self._plugins.pop(plugin_id, None)
            if plugin:
                logger.info(f"PluginRegistry: Unregistered plugin '{plugin_id}'.")
                return True
        return False

    def get_plugin(self, plugin_id: str) -> BasePlugin | None:
        """Get plugin instance by ID."""
        with self._lock:
            return self._plugins.get(plugin_id)

    def disable_plugin(self, plugin_id: str) -> None:
        """Mark a plugin as disabled."""
        with self._lock:
            self._disabled_plugins.add(plugin_id)
            logger.info(f"PluginRegistry: Disabled plugin '{plugin_id}'.")

    def enable_plugin(self, plugin_id: str) -> None:
        """Enable a previously disabled plugin."""
        with self._lock:
            self._disabled_plugins.discard(plugin_id)
            logger.info(f"PluginRegistry: Enabled plugin '{plugin_id}'.")

    def is_disabled(self, plugin_id: str) -> bool:
        """Check if plugin is disabled."""
        with self._lock:
            return plugin_id in self._disabled_plugins

    def list_plugins(self) -> list[dict[str, Any]]:
        """List summary metadata for all registered plugins."""
        with self._lock:
            result = []
            for pid, plugin in self._plugins.items():
                meta = plugin.metadata
                result.append(
                    {
                        "plugin_id": pid,
                        "name": meta.name,
                        "version": meta.version,
                        "author": meta.author,
                        "description": meta.description,
                        "state": plugin.state.name,
                        "disabled": pid in self._disabled_plugins,
                    }
                )
            return result
