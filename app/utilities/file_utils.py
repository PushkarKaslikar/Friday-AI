"""File management utilities for safe JSON and text I/O operations."""

import json
from pathlib import Path
from typing import Any

from app.exceptions.config import ConfigurationError


def read_json_file(file_path: str | Path) -> dict[str, Any]:
    """Safely read and parse a JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Dictionary containing parsed JSON data.

    Raises:
        ConfigurationError: If the file does not exist, cannot be read, or is invalid JSON.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise ConfigurationError(f"JSON file does not exist: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ConfigurationError(
                    f"Root JSON element in {path} must be a dictionary."
                )
            return data
    except json.JSONDecodeError as exc:
        raise ConfigurationError(f"Failed to parse JSON file {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigurationError(f"Failed to read file {path}: {exc}") from exc


def write_json_file(
    file_path: str | Path, data: dict[str, Any], indent: int = 2
) -> None:
    """Safely write dictionary data to a JSON file.

    Args:
        file_path: Path to the JSON file.
        data: Dictionary data to write.
        indent: Indentation level.
    """
    path = Path(file_path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    except OSError as exc:
        raise ConfigurationError(f"Failed to write JSON file {path}: {exc}") from exc
