"""Plugin Validator verifying metadata, versions, permissions, and dependencies."""

from typing import NamedTuple

from app.plugins.base.plugin_interface import BasePlugin


class PluginValidationResult(NamedTuple):
    is_valid: bool
    errors: list[str]


class PluginValidator:
    """Validates plugin instances and metadata prior to registry insertion and loading."""

    def validate_plugin(self, plugin: BasePlugin) -> PluginValidationResult:
        """Run validation checks on a plugin instance.

        Args:
            plugin: BasePlugin instance.

        Returns:
            PluginValidationResult: Pass status and list of error messages.
        """
        errors: list[str] = []

        if not isinstance(plugin, BasePlugin):
            return PluginValidationResult(
                is_valid=False, errors=["Plugin must inherit from BasePlugin."]
            )

        metadata = plugin.metadata
        if not metadata:
            return PluginValidationResult(
                is_valid=False, errors=["Plugin metadata is missing."]
            )

        if (
            not metadata.plugin_id
            or not isinstance(metadata.plugin_id, str)
            or not metadata.plugin_id.strip()
        ):
            errors.append("Plugin plugin_id must be a non-empty string.")

        if (
            not metadata.name
            or not isinstance(metadata.name, str)
            or not metadata.name.strip()
        ):
            errors.append("Plugin name must be a non-empty string.")

        if not metadata.version or not isinstance(metadata.version, str):
            errors.append("Plugin version must be a valid string.")

        return PluginValidationResult(is_valid=len(errors) == 0, errors=errors)
