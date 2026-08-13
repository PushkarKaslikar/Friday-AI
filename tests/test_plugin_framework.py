"""Unit tests for Plugin Framework components."""

from app.plugins.base.plugin_interface import BasePlugin, PluginMetadata
from app.plugins.registry.plugin_registry import PluginRegistry
from app.plugins.validation.plugin_validator import PluginValidator


class DummyPlugin(BasePlugin):
    """Dummy plugin for unit testing."""

    def __init__(self):
        meta = PluginMetadata(
            plugin_id="dummy_plugin",
            name="Dummy Test Plugin",
            version="1.0.0",
            author="Friday Team",
            description="Testing plugin implementation",
        )
        super().__init__(metadata=meta)

    def _do_initialize(self) -> None:
        pass

    def _do_start(self) -> None:
        pass

    def _do_stop(self) -> None:
        pass


def test_plugin_validator_and_registry():
    validator = PluginValidator()
    registry = PluginRegistry()

    plugin = DummyPlugin()
    validation = validator.validate_plugin(plugin)
    assert validation.is_valid is True
    assert len(validation.errors) == 0

    registered = registry.register(plugin)
    assert registered is True
    assert registry.get_plugin("dummy_plugin") == plugin

    plugins = registry.list_plugins()
    assert len(plugins) == 1
    assert plugins[0]["plugin_id"] == "dummy_plugin"
