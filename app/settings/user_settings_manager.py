"""User Settings Manager for reading, updating, persisting, and notifying settings changes."""

import threading
from pathlib import Path
from typing import Any, Optional

from app.config.backup_manager import ConfigBackupManager
from app.config.migrator import ConfigMigrator
from app.constants.paths import SETTINGS_FILE
from app.logging import logger
from app.services.events.event_bus import EventBus
from app.services.events.event_models import SettingsChanged
from app.utilities.file_utils import read_json_file, write_json_file


class UserSettingsManager:
    """Manages application setting categories, persistence, backups, and EventBus notifications."""

    _instance: Optional["UserSettingsManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        settings_file: str | Path | None = None,
        event_bus: EventBus | None = None,
        backup_manager: ConfigBackupManager | None = None,
    ) -> None:
        if getattr(self, "_initialized", False):
            return

        self.settings_file = Path(settings_file or SETTINGS_FILE).resolve()
        self.event_bus = event_bus or EventBus()
        self.backup_manager = backup_manager or ConfigBackupManager()
        self.migrator = ConfigMigrator()

        self._lock = threading.RLock()
        self._settings_data: dict[str, Any] = {}
        self._initialized = True

        self.load_settings()

    def load_settings(self) -> dict[str, Any]:
        """Load, migrate, and validate settings from JSON file."""
        with self._lock:
            if not self.settings_file.exists():
                self._settings_data = self._get_default_settings()
                self.save_settings(create_backup=False)
                return self._settings_data

            try:
                data = read_json_file(self.settings_file)
                self._settings_data = self.migrator.migrate(data)
                logger.info("UserSettingsManager: Successfully loaded settings.")
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"UserSettingsManager: Failed to read settings ({exc}). Restoring defaults."
                )
                self._settings_data = self._get_default_settings()
                self.save_settings(create_backup=True)

            return self._settings_data

    def get(self, category: str, key: str, default: Any = None) -> Any:
        """Get specific setting value by category and key."""
        with self._lock:
            cat_data = self._settings_data.get(category, {})
            if isinstance(cat_data, dict):
                return cat_data.get(key, default)
            return default

    def set(self, category: str, key: str, value: Any, auto_save: bool = True) -> None:
        """Set specific setting value and optionally persist changes."""
        with self._lock:
            if category not in self._settings_data or not isinstance(
                self._settings_data[category], dict
            ):
                self._settings_data[category] = {}

            self._settings_data[category][key] = value
            logger.info(
                f"UserSettingsManager: Updated setting '{category}.{key}' = {value}."
            )

            if auto_save:
                self.save_settings()

            self.event_bus.publish(SettingsChanged(changed_keys=[f"{category}.{key}"]))

    def save_settings(self, create_backup: bool = True) -> None:
        """Persist current settings data to JSON file."""
        with self._lock:
            if create_backup and self.settings_file.exists():
                try:
                    self.backup_manager.create_backup(self.settings_file)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        f"UserSettingsManager: Failed to create backup before save: {exc}"
                    )

            write_json_file(self.settings_file, self._settings_data)
            logger.info("UserSettingsManager: Saved settings to disk.")

    def restore_defaults(self) -> None:
        """Reset configuration to factory defaults."""
        with self._lock:
            self.backup_manager.create_backup(self.settings_file)
            self._settings_data = self._get_default_settings()
            self.save_settings(create_backup=False)
            self.event_bus.publish(SettingsChanged(changed_keys=["all"]))
            logger.info("UserSettingsManager: Restored default configuration.")

    def _get_default_settings(self) -> dict[str, Any]:
        """Return fallback default configuration dictionary."""
        return {
            "version": "1.0",
            "general": {
                "app_name": "Friday AI Assistant",
                "environment": "development",
                "autostart": False,
            },
            "appearance": {
                "theme": "dark",
                "ui_scaling": 1.0,
                "animations_enabled": True,
                "window_transparency": False,
            },
            "performance": {
                "max_worker_threads": 8,
                "background_monitoring": True,
            },
            "plugins": {
                "enabled": True,
                "auto_load": True,
            },
            "tools": {
                "tool_engine_enabled": True,
                "default_timeout": 10.0,
                "default_risk_policy": "STRICT",
            },
            "tool_execution": {
                "enabled": True,
                "default_timeout": 10.0,
                "max_timeout": 60.0,
                "max_retries": 2,
                "history_limit": 100,
                "allow_background_execution": True,
                "confirmation_timeout": 30.0,
                "development_mode": True,
            },
            "diagnostics": {
                "health_check_interval_sec": 30,
                "metrics_collection": True,
            },
            "developer": {
                "developer_mode": False,
                "verbose_logging": False,
            },
            "ai": {},
            "audio": {},
            "automation": {},
        }
