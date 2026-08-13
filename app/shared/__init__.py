"""Shared layer containing cross-cutting models, data transfer objects, and types."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExecutionResult:
    """Standard execution response object."""

    success: bool
    message: str
    data: dict[str, Any] | None = None
    error: str | None = None


__all__ = ["ExecutionResult"]
