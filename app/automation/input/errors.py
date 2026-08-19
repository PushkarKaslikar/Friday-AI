"""Exception types for Phase 6.2 Mouse, Keyboard & Human-Like Input Control Engine."""

from typing import Any

from app.automation.errors import AutomationError


class InputEngineError(AutomationError):
    """Base exception for all input engine errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, details=details, cause=cause)


class InvalidTargetError(InputEngineError):
    """Raised when an input target (coordinates or UIA element) is invalid or unavailable."""


class InvalidCoordinatesError(InputEngineError):
    """Raised when coordinates fall outside valid virtual screen boundaries."""


class InvalidKeyError(InputEngineError):
    """Raised when an invalid or unmapped keyboard key name or code is supplied."""


class InputBusyError(InputEngineError):
    """Raised when another input sequence currently owns the input channel."""


class InputCancelledError(InputEngineError):
    """Raised when an input operation is cancelled via CancellationToken."""


class InputInterruptedError(InputEngineError):
    """Raised when physical user activity (mouse or keyboard) interrupts automated input."""


class FailsafeAbortedError(InputEngineError):
    """Raised when emergency top-left corner mouse failsafe triggers during automation."""


class InputTimeoutError(InputEngineError):
    """Raised when an input operation exceeds maximum allowed duration."""


class BackendUnavailableError(InputEngineError):
    """Raised when the requested input backend (Native or PyAutoGUI) is unavailable."""
