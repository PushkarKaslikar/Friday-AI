"""Centralized production-grade logging infrastructure using Loguru with multi-channel sinks."""

import sys
from collections.abc import Callable
from typing import Any

from loguru import logger

from app.config.models import LoggingSettings
from app.constants.defaults import DEFAULT_LOG_FORMAT
from app.constants.paths import APP_LOG_FILE, ERROR_LOG_FILE, LOGS_DIR
from app.utilities.path_utils import ensure_directory_exists

PERFORMANCE_LOG_FILE = LOGS_DIR / "performance.log"
PLUGINS_LOG_FILE = LOGS_DIR / "plugins.log"
CRASH_LOG_FILE = LOGS_DIR / "crash.log"


def _safe_add_file_sink(
    filepath: Any,
    level: str,
    rotation: str,
    retention: str,
    filter_func: Callable[[dict], bool] | None = None,
    backtrace: bool = False,
    diagnose: bool = False,
) -> None:
    """Safely register a Loguru file sink with fallback if Windows file locking prevents rotation."""
    kwargs: dict[str, Any] = {
        "format": DEFAULT_LOG_FORMAT,
        "level": level,
        "encoding": "utf-8",
        "enqueue": True,
        "catch": True,
        "delay": True,
    }
    if filter_func is not None:
        kwargs["filter"] = filter_func
    if backtrace:
        kwargs["backtrace"] = True
    if diagnose:
        kwargs["diagnose"] = True

    try:
        logger.add(filepath, rotation=rotation, retention=retention, **kwargs)
    except (PermissionError, OSError):
        # Fallback to non-rotating file sink if file rotation is blocked on Windows
        try:
            logger.add(filepath, rotation=None, **kwargs)
        except (PermissionError, OSError):
            sys.stderr.write(
                f"[LoggingWarning] Could not open log sink for {filepath}\n"
            )


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

            # Application Log File
            _safe_add_file_sink(
                APP_LOG_FILE,
                level=log_level,
                rotation=rotation_str,
                retention=retention_str,
                backtrace=True,
                diagnose=True,
            )

            # Error Log File
            _safe_add_file_sink(
                ERROR_LOG_FILE,
                level="WARNING",
                rotation=rotation_str,
                retention=retention_str,
                backtrace=True,
                diagnose=True,
            )

            # Performance Log File
            _safe_add_file_sink(
                PERFORMANCE_LOG_FILE,
                level="INFO",
                rotation=rotation_str,
                retention=retention_str,
                filter_func=lambda record: "performance" in record["extra"]
                or "Performance" in record["message"],
            )

            # Plugins Log File
            _safe_add_file_sink(
                PLUGINS_LOG_FILE,
                level="INFO",
                rotation=rotation_str,
                retention=retention_str,
                filter_func=lambda record: "plugin" in record["extra"]
                or "Plugin" in record["message"],
            )

            # Crash Log File
            _safe_add_file_sink(
                CRASH_LOG_FILE,
                level="CRITICAL",
                rotation=rotation_str,
                retention=retention_str,
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
