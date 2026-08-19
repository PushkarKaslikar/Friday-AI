"""Exception types for Phase 6.3 Window Management, Desktop Control, Clipboard & Screen Inspection Engine."""

from typing import Any

from app.automation.errors import AutomationError


class DesktopError(AutomationError):
    """Base exception for all desktop control subsystem errors."""

    def __init__(
        self,
        message: str,
        details: dict[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message, details=details, cause=cause)


class WindowNotFoundError(DesktopError):
    """Raised when a specified window handle or title target is not found."""


class WindowClosedError(DesktopError):
    """Raised when attempting an operation on a window that has been destroyed or closed."""


class FocusDeniedError(DesktopError):
    """Raised when Windows foreground focus restrictions prevent window activation."""


class InvalidGeometryError(DesktopError):
    """Raised when invalid window dimensions or position coordinates are specified."""


class MonitorNotFoundError(DesktopError):
    """Raised when a requested monitor ID or index is not found in the active topology."""


class VirtualDesktopUnavailableError(DesktopError):
    """Raised when Windows virtual desktop APIs are unsupported or unavailable."""


class ScreenCaptureFailedError(DesktopError):
    """Raised when a screen capture operation fails."""


class ScreenCaptureTimeoutError(DesktopError):
    """Raised when screen capture exceeds maximum allowed duration."""


class ClipboardUnavailableError(DesktopError):
    """Raised when the Windows clipboard cannot be opened or accessed."""


class ClipboardFormatUnsupportedError(DesktopError):
    """Raised when requested clipboard format is unsupported or empty."""


class ClipboardSizeLimitError(DesktopError):
    """Raised when clipboard text/HTML payload exceeds maximum allowed size cap."""


class WorkspaceRestoreFailedError(DesktopError):
    """Raised when restoring a workspace layout fails."""
