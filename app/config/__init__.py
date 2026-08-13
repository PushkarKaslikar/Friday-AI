"""Configuration package for Friday AI Assistant."""

from app.config.manager import ConfigurationManager
from app.config.models import AppInfoSettings, LoggingSettings, Settings, UISettings

__all__ = [
    "AppInfoSettings",
    "ConfigurationManager",
    "LoggingSettings",
    "Settings",
    "UISettings",
]
