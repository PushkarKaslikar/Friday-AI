"""Base Plugin abstract interface and metadata contracts for extensible plugins."""

from dataclasses import dataclass, field
from typing import Any

from app.services.base.service_interface import BaseService


@dataclass
class PluginMetadata:
    """Metadata specification for Friday AI plugins."""

    plugin_id: str
    name: str
    version: str
    author: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)


class BasePlugin(BaseService):
    """Abstract Base Class for all external Friday AI Assistant plugins."""

    def __init__(self, metadata: PluginMetadata) -> None:
        super().__init__(name=f"Plugin_{metadata.plugin_id}", is_critical=False)
        self._metadata = metadata
        self._plugin_config: dict[str, Any] = {}

    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return self._metadata

    @property
    def plugin_id(self) -> str:
        """Get unique plugin ID."""
        return self._metadata.plugin_id

    def set_config(self, config: dict[str, Any]) -> None:
        """Provide plugin-specific configuration data."""
        self._plugin_config = config

    def health_check(self) -> dict[str, Any]:
        """Collect plugin health status payload."""
        data = super().health_check()
        data["plugin_id"] = self.plugin_id
        data["version"] = self.metadata.version
        return data
