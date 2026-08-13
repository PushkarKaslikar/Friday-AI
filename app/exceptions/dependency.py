"""Dependency injection exceptions."""

from app.exceptions.base import FridayBaseException


class DependencyError(FridayBaseException):
    """Raised when dependency container resolution or binding fails."""
