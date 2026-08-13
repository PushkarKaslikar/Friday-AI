"""Startup Manager managing Windows autostart configuration strategies."""

import os
import sys
from pathlib import Path

from app.constants.application import APP_NAME
from app.logging import logger
from app.platform.registry.registry_manager import RUN_REG_KEY_PATH, RegistryManager


class StartupManager:
    """Manages application startup configuration using Registry or Startup Folder strategy."""

    def __init__(self, registry_manager: RegistryManager | None = None) -> None:
        self.registry_manager = registry_manager or RegistryManager()

    def get_executable_command(self) -> str:
        """Get target executable launch command string."""
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}" --minimized'
        return f'"{sys.executable}" "{Path(sys.argv[0]).resolve()}" --minimized'

    def is_startup_enabled(self) -> bool:
        """Check if Windows startup is enabled in Registry."""
        val = self.registry_manager.get_value(RUN_REG_KEY_PATH, APP_NAME)
        return val is not None

    def enable_startup(self) -> bool:
        """Enable application startup in Windows Registry.

        Returns:
            bool: True if startup registration succeeded.
        """
        cmd = self.get_executable_command()
        success = self.registry_manager.set_value(RUN_REG_KEY_PATH, APP_NAME, cmd)
        if success:
            logger.info("StartupManager: Enabled Windows autostart.")
        return success

    def disable_startup(self) -> bool:
        """Disable application startup in Windows Registry.

        Returns:
            bool: True if startup removal succeeded.
        """
        success = self.registry_manager.delete_value(RUN_REG_KEY_PATH, APP_NAME)
        if success:
            logger.info("StartupManager: Disabled Windows autostart.")
        return success

    def toggle_startup(self) -> bool:
        """Toggle startup state between enabled and disabled.

        Returns:
            bool: New startup state (True = enabled, False = disabled).
        """
        if self.is_startup_enabled():
            self.disable_startup()
            return False

        self.enable_startup()
        return True

    def get_startup_folder_path(self) -> Path:
        """Get user Windows Startup folder path."""
        appdata = os.getenv("APPDATA", "")
        return Path(appdata) / r"Microsoft\Windows\Start Menu\Programs\Startup"
