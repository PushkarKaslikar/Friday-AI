"""Plugins package for Friday AI Assistant plugin foundation."""

from app.plugins.base.plugin_interface import BasePlugin, PluginMetadata
from app.plugins.loader.plugin_loader import PluginLoader
from app.plugins.registry.plugin_registry import PluginRegistry
from app.plugins.validation.plugin_validator import (
    PluginValidationResult,
    PluginValidator,
)

__all__ = [
    "BasePlugin",
    "PluginLoader",
    "PluginMetadata",
    "PluginRegistry",
    "PluginValidationResult",
    "PluginValidator",
]
