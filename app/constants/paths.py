"""Path constants for the application directory layout."""

from pathlib import Path
from typing import Final

# Root directory of the repository (where main.py is located)
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parent.parent.parent

# Application internal directory
APP_DIR: Final[Path] = PROJECT_ROOT / "app"

# Configuration directory & settings file
CONFIG_DIR: Final[Path] = PROJECT_ROOT / "config"
SETTINGS_FILE: Final[Path] = CONFIG_DIR / "settings.json"
ENV_FILE: Final[Path] = PROJECT_ROOT / ".env"
ENV_EXAMPLE_FILE: Final[Path] = PROJECT_ROOT / ".env.example"

# Logging directory & log files
LOGS_DIR: Final[Path] = PROJECT_ROOT / "logs"
APP_LOG_FILE: Final[Path] = LOGS_DIR / "application.log"
ERROR_LOG_FILE: Final[Path] = LOGS_DIR / "errors.log"

# Asset & documentation directories
ASSETS_DIR: Final[Path] = PROJECT_ROOT / "assets"
DOCS_DIR: Final[Path] = PROJECT_ROOT / "docs"
SCRIPTS_DIR: Final[Path] = PROJECT_ROOT / "scripts"
TESTS_DIR: Final[Path] = PROJECT_ROOT / "tests"

# List of all required directories that must exist on startup
REQUIRED_DIRECTORIES: Final[tuple[Path, ...]] = (
    CONFIG_DIR,
    LOGS_DIR,
    ASSETS_DIR,
    DOCS_DIR,
    SCRIPTS_DIR,
)
