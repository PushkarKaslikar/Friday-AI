"""Bootstrap and environment initialization exceptions."""

from app.exceptions.base import FridayBaseException


class InitializationError(FridayBaseException):
    """Raised when application bootstrapping sequence fails."""


class EnvironmentValidationError(InitializationError):
    """Raised when system environment (OS, Python version, permissions, paths) is invalid."""
