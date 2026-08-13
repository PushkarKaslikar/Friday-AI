"""Centralized production-grade logging infrastructure using Loguru with multi-channel sinks."""

import sys

from loguru import logger

from app.config.models import LoggingSettings
from app.constants.defaults import DEFAULT_LOG_FORMAT
from app.constants.paths import APP_LOG_FILE, ERROR_LOG_FILE, LOGS_DIR
from app.utilities.path_utils import ensure_directory_exists

PERFORMANCE_LOG_FILE = LOGS_DIR / "performance.log"
PLUGINS_LOG_FILE = LOGS_DIR / "plugins.log"
CRASH_LOG_FILE = LOGS_DIR / "crash.log"


class LoggingManager:
    """Manages system logging sinks, formatters, multi-channel log files, and lifecycle hooks using Loguru."""

    def __init__(self, settings: LoggingSettings | None = None) -> None:
        self.settings = settings or LoggingSettings()
        self._initialized = False

    def setup_logging(self) -> None:
        """Initialize Loguru logging sinks (Console, Application log, Error log, Performance log, Plugins log, Crash log)."""
        # Ensure log directory exists
        ensure_directory_exists(LOGS_DIR)

        # Remove default Loguru handler
        logger.remove()

        log_level = self.settings.level

        # 1. Console Sink
        if self.settings.log_to_console:
            logger.add(
                sys.stdout,
                format=DEFAULT_LOG_FORMAT,
                level=log_level,
                colorize=True,
                backtrace=True,
                diagnose=True,
            )

        # 2. File Sinks
        if self.settings.log_to_file:
            rotation_str = f"{self.settings.max_file_size_mb} MB"
            retention_str = f"{self.settings.retention_days} days"

            # Application Log File (all logs at configured log level)
            logger.add(
                APP_LOG_FILE,
                format=DEFAULT_LOG_FORMAT,
                level=log_level,
                rotation=rotation_str,
                retention=retention_str,
                encoding="utf-8",
                backtrace=True,
                diagnose=True,
                enqueue=True,
            )

            # Error Log File (WARNING and above only)
            logger.add(
                ERROR_LOG_FILE,
                format=DEFAULT_LOG_FORMAT,
                level="WARNING",
                rotation=rotation_str,
                retention=retention_str,
                encoding="utf-8",
                backtrace=True,
                diagnose=True,
                enqueue=True,
            )

            # Performance Log File (filter for performance channel messages)
            logger.add(
                PERFORMANCE_LOG_FILE,
                format=DEFAULT_LOG_FORMAT,
                level="INFO",
                filter=lambda record: "performance" in record["extra"]
                or "Performance" in record["message"],
                rotation=rotation_str,
                retention=retention_str,
                encoding="utf-8",
                enqueue=True,
            )

            # Plugins Log File
            logger.add(
                PLUGINS_LOG_FILE,
                format=DEFAULT_LOG_FORMAT,
                level="INFO",
                filter=lambda record: "plugin" in record["extra"]
                or "Plugin" in record["message"],
                rotation=rotation_str,
                retention=retention_str,
                encoding="utf-8",
                enqueue=True,
            )

            # Crash Log File
            logger.add(
                CRASH_LOG_FILE,
                format=DEFAULT_LOG_FORMAT,
                level="CRITICAL",
                rotation=rotation_str,
                retention=retention_str,
                encoding="utf-8",
                enqueue=True,
            )

        self._initialized = True
        logger.info("Logging subsystem initialized with multi-channel log sinks.")

    def log_startup(self, app_name: str, version: str, environment: str) -> None:
        """Log standardized application startup event."""
        logger.info("=" * 60)
        logger.info(f"Starting {app_name} v{version} [{environment.upper()}]")
        logger.info("=" * 60)

    def log_shutdown(self, app_name: str) -> None:
        """Log standardized application shutdown event."""
        logger.info("-" * 60)
        logger.info(f"Shutting down {app_name} gracefully.")
        logger.info("-" * 60)

    @property
    def is_initialized(self) -> bool:
        """Return True if logging setup has completed."""
        return self._initialized
