"""Plugin Loader discovering, dynamically importing, validating, and managing plugin packages."""

import importlib.util
from pathlib import Path

from app.constants.paths import PROJECT_ROOT
from app.logging import logger
from app.plugins.base.plugin_interface import BasePlugin
from app.plugins.registry.plugin_registry import PluginRegistry
from app.plugins.validation.plugin_validator import PluginValidator
from app.utilities.path_utils import ensure_directory_exists

DEFAULT_PLUGINS_DIR = PROJECT_ROOT / "plugins"


class PluginLoader:
    """Discovers external plugins in plugins/ directory, validates metadata, and loads them dynamically."""

    def __init__(
        self,
        plugins_dir: str | Path | None = None,
        registry: PluginRegistry | None = None,
        validator: PluginValidator | None = None,
    ) -> None:
        self.plugins_dir = ensure_directory_exists(plugins_dir or DEFAULT_PLUGINS_DIR)
        self.registry = registry or PluginRegistry()
        self.validator = validator or PluginValidator()

    def discover_and_load(self) -> int:
        """Scan plugins directory for Python plugin packages, validate, and register them.

        Returns:
            int: Count of successfully loaded plugins.
        """
        logger.info(f"PluginLoader: Scanning for plugins in '{self.plugins_dir}'...")

        if not self.plugins_dir.exists():
            return 0

        loaded_count = 0
        for entry in self.plugins_dir.iterdir():
            if entry.is_dir() and (entry / "__init__.py").exists():
                plugin_instance = self._load_plugin_from_directory(entry)
                if plugin_instance:
                    validation = self.validator.validate_plugin(plugin_instance)
                    if validation.is_valid:
                        if self.registry.register(plugin_instance):
                            loaded_count += 1
                    else:
                        logger.warning(
                            f"PluginLoader: Rejected plugin in '{entry.name}': {validation.errors}"
                        )

        logger.info(f"PluginLoader: Discovery complete. Loaded {loaded_count} plugins.")
        return loaded_count

    def _load_plugin_from_directory(self, plugin_dir: Path) -> BasePlugin | None:
        """Dynamically import plugin module from directory."""
        init_file = plugin_dir / "__init__.py"
        module_name = f"friday_plugin_{plugin_dir.name}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, init_file)
            if not spec or not spec.loader:
                return None

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find BasePlugin subclass in module attributes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, BasePlugin)
                    and attr is not BasePlugin
                ):
                    plugin_instance = attr()
                    return plugin_instance
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"PluginLoader: Exception loading plugin from '{plugin_dir.name}': {exc}"
            )
        return None
