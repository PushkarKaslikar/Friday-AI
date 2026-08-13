"""Application metadata constants."""

import sys
from typing import Final

APP_NAME: Final[str] = "Friday AI Assistant"
APP_DESCRIPTION: Final[str] = (
    "Fully local, high-performance personal AI desktop assistant for Windows."
)
APP_VERSION: Final[str] = "1.0.0"
APP_AUTHOR: Final[str] = "Friday AI Team"

# Target Platform Constraints
MIN_PYTHON_VERSION: Final[tuple[int, int]] = (3, 12)
PRIMARY_OS: Final[str] = "Windows 11"
SECONDARY_OS: Final[str] = "Windows 10"

IS_WINDOWS: Final[bool] = sys.platform.startswith("win")
