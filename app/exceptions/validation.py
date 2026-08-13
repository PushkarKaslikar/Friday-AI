"""Validation exceptions."""

from app.exceptions.base import FridayBaseException


class ValidationError(FridayBaseException):
    """Raised when data or input validation fails."""
