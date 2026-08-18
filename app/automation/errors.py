"""Exception types for the Phase 6.1 UI Automation Foundation subsystem."""

from typing import Any

from app.exceptions.base import FridayBaseException


class AutomationError(FridayBaseException):
    """Base exception for all UI Automation subsystem errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, details=details, cause=cause)


class UIAEngineError(AutomationError):
    """Raised when the UIA engine initialization or backend operation fails."""


class ElementNotFoundError(AutomationError):
    """Raised when a specified UI element cannot be located."""


class ElementStaleError(AutomationError):
    """Raised when a UI element reference is no longer valid or destroyed."""


class ElementInvalidError(AutomationError):
    """Raised when an operation is performed on an invalid or unsuited element."""


class PatternNotSupportedError(AutomationError):
    """Raised when a control pattern operation is attempted on an element that does not support it."""


class AmbiguousWindowError(AutomationError):
    """Raised when multiple candidate windows match search criteria."""


class AmbiguousElementError(AutomationError):
    """Raised when multiple elements match search criteria expecting a unique result."""


class ProcessExitedError(AutomationError):
    """Raised when attempting to inspect or interact with a process that has exited."""


class TreeTraversalError(AutomationError):
    """Raised when traversing the UI element tree fails or violates bounds unexpectedly."""
