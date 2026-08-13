"""Default configuration and system constants."""

from typing import Final

# Application Defaults
DEFAULT_ENVIRONMENT: Final[str] = "development"
DEFAULT_DEBUG: Final[bool] = True

# UI Defaults
DEFAULT_THEME: Final[str] = "dark"
DEFAULT_START_MINIMIZED: Final[bool] = False
DEFAULT_AUTO_START: Final[bool] = False

# Logging Defaults
DEFAULT_LOG_LEVEL: Final[str] = "INFO"
DEFAULT_LOG_TO_CONSOLE: Final[bool] = True
DEFAULT_LOG_TO_FILE: Final[bool] = True
DEFAULT_MAX_FILE_SIZE_MB: Final[int] = 10
DEFAULT_RETENTION_DAYS: Final[int] = 30
DEFAULT_LOG_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)
