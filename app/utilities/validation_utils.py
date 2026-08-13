"""General validation helper functions."""

from typing import Any


def validate_non_empty_string(value: Any, field_name: str) -> str:
    """Validate that a value is a non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def validate_positive_integer(value: Any, field_name: str) -> int:
    """Validate that a value is a positive integer (> 0)."""
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer greater than 0.")
    return value
