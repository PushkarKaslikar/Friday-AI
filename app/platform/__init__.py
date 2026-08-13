"""Platform package for Friday AI Assistant Windows platform integration."""

from app.platform.identity.app_identity import APP_IDENTITY, ApplicationMetadata
from app.platform.info.system_info import SystemInfo
from app.platform.notifications.notification_manager import (
    NotificationLevel,
    NotificationManager,
)
from app.platform.process.process_manager import ProcessManager
from app.platform.registry.registry_manager import RegistryManager
from app.platform.resources.resource_monitor import ResourceMonitor
from app.platform.startup.startup_manager import StartupManager
from app.platform.version.version_manager import SemanticVersion, VersionManager

__all__ = [
    "APP_IDENTITY",
    "ApplicationMetadata",
    "NotificationLevel",
    "NotificationManager",
    "ProcessManager",
    "RegistryManager",
    "ResourceMonitor",
    "SemanticVersion",
    "StartupManager",
    "SystemInfo",
    "VersionManager",
]
