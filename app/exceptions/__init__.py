"""Custom exception hierarchy for Friday AI Assistant."""

from app.exceptions.base import FridayBaseException
from app.exceptions.bootstrap import EnvironmentValidationError, InitializationError
from app.exceptions.config import ConfigurationError
from app.exceptions.dependency import DependencyError
from app.exceptions.validation import ValidationError

__all__ = [
    "ConfigurationError",
    "DependencyError",
    "EnvironmentValidationError",
    "FridayBaseException",
    "InitializationError",
    "ValidationError",
]
