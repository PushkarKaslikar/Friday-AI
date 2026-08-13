"""Base exception for the Friday AI Assistant system."""

from typing import Any


class FridayBaseException(Exception):
    """Base exception class for all custom Friday AI exceptions."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.cause = cause

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message
