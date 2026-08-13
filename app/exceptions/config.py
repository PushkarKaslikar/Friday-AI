"""Configuration-related exceptions."""

from app.exceptions.base import FridayBaseException


class ConfigurationError(FridayBaseException):
    """Raised when configuration loading, parsing, or validation fails."""
