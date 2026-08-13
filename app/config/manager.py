"""Configuration Manager responsible for loading and resolving application settings."""

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import ValidationError as PydanticValidationError

from app.config.models import AppInfoSettings, LoggingSettings, Settings, UISettings
from app.constants.paths import ENV_FILE, SETTINGS_FILE
from app.exceptions.config import ConfigurationError
from app.utilities.file_utils import read_json_file


class ConfigurationManager:
    """Manages application settings loading from JSON, .env, and environment variables."""

    def __init__(
        self,
        json_path: str | Path | None = None,
        env_path: str | Path | None = None,
    ) -> None:
        self.json_path = Path(json_path).resolve() if json_path else SETTINGS_FILE
        self.env_path = Path(env_path).resolve() if env_path else ENV_FILE
        self._settings: Settings | None = None

    def load_settings(self) -> Settings:
        """Load and resolve application settings from all configuration sources.

        Precedence (highest to lowest):
        1. Environment variables (FRIDAY_*)
        2. .env file
        3. config/settings.json file
        4. Default values

        Returns:
            Settings: Validated configuration instance.

        Raises:
            ConfigurationError: If loading or validating settings fails.
        """
        # Load .env file if present
        if self.env_path.exists():
            load_dotenv(dotenv_path=self.env_path, override=True)

        json_data: dict = {}
        if self.json_path.exists():
            try:
                json_data = read_json_file(self.json_path)
            except Exception as exc:
                raise ConfigurationError(
                    f"Failed to load JSON configuration from {self.json_path}: {exc}",
                    cause=exc,
                ) from exc

        app_dict = json_data.get("app", {})
        ui_dict = json_data.get("ui", {})
        logging_dict = json_data.get("logging", {})

        # Environment variable overrides
        if env_app_name := os.getenv("FRIDAY_APP_NAME"):
            app_dict["name"] = env_app_name
        if env_stage := os.getenv("FRIDAY_ENVIRONMENT"):
            app_dict["environment"] = env_stage
        if env_debug := os.getenv("FRIDAY_DEBUG"):
            app_dict["debug"] = env_debug.lower() in ("true", "1", "yes")

        if env_theme := os.getenv("FRIDAY_THEME"):
            ui_dict["theme"] = env_theme
        if env_minimized := os.getenv("FRIDAY_START_MINIMIZED"):
            ui_dict["start_minimized"] = env_minimized.lower() in ("true", "1", "yes")
        if env_autostart := os.getenv("FRIDAY_AUTO_START"):
            ui_dict["auto_start"] = env_autostart.lower() in ("true", "1", "yes")

        if env_log_level := os.getenv("FRIDAY_LOG_LEVEL"):
            logging_dict["level"] = env_log_level.upper()

        try:
            app_settings = AppInfoSettings(**app_dict)
            ui_settings = UISettings(**ui_dict)
            logging_settings = LoggingSettings(**logging_dict)
            self._settings = Settings(
                app=app_settings,
                ui=ui_settings,
                logging=logging_settings,
            )
            return self._settings
        except PydanticValidationError as exc:
            raise ConfigurationError(
                f"Configuration validation error: {exc}",
                details={"errors": exc.errors()},
                cause=exc,
            ) from exc

    @property
    def settings(self) -> Settings:
        """Get the loaded settings instance. Loads settings if not already loaded."""
        if self._settings is None:
            return self.load_settings()
        return self._settings
