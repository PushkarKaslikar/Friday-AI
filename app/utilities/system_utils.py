"""System and runtime environment utility helpers."""

import datetime
import platform
import sys
from typing import NamedTuple

from app.constants.application import MIN_PYTHON_VERSION


class SystemInfo(NamedTuple):
    python_version: str
    os_name: str
    os_release: str
    os_version: str
    architecture: str


def get_system_info() -> SystemInfo:
    """Collect operating system and runtime system information."""
    return SystemInfo(
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        os_name=platform.system(),
        os_release=platform.release(),
        os_version=platform.version(),
        architecture=platform.machine(),
    )


def is_python_version_supported() -> bool:
    """Check if current Python runtime satisfies minimum required version (>= 3.12)."""
    return sys.version_info >= MIN_PYTHON_VERSION


def get_timestamp_str() -> str:
    """Return timestamp string for diagnostic and model timestamp fields."""
    return str(datetime.datetime.now())  # noqa: DTZ005
