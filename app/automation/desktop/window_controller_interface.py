"""Abstract interface defining Phase 6.3 WindowController contracts."""

from abc import ABC, abstractmethod

from app.automation.desktop.models import (
    DesktopWindow,
    SnapPosition,
    WindowOperationResult,
)


class IWindowController(ABC):
    """Abstract interface for Windows window discovery, focus, geometry manipulation, and snapping."""

    @abstractmethod
    def list_windows(self, include_hidden: bool = False) -> list[DesktopWindow]:
        """List all top-level desktop windows."""

    @abstractmethod
    def get_active_window(self) -> DesktopWindow | None:
        """Get DesktopWindow model for the currently active foreground window."""

    @abstractmethod
    def get_window_by_hwnd(self, hwnd: int) -> DesktopWindow:
        """Get DesktopWindow for a specific HWND handle."""

    @abstractmethod
    def focus_window(self, hwnd: int) -> WindowOperationResult:
        """Bring window to foreground and restore focus."""

    @abstractmethod
    def minimize_window(self, hwnd: int) -> WindowOperationResult:
        """Minimize window."""

    @abstractmethod
    def maximize_window(self, hwnd: int) -> WindowOperationResult:
        """Maximize window to monitor work area."""

    @abstractmethod
    def restore_window(self, hwnd: int) -> WindowOperationResult:
        """Restore window to normal state."""

    @abstractmethod
    def move_window(self, hwnd: int, x: int, y: int) -> WindowOperationResult:
        """Move window to absolute virtual screen coordinates."""

    @abstractmethod
    def resize_window(
        self, hwnd: int, width: int, height: int
    ) -> WindowOperationResult:
        """Resize window dimensions."""

    @abstractmethod
    def snap_window(self, hwnd: int, position: SnapPosition) -> WindowOperationResult:
        """Snap window to monitor work area position."""

    @abstractmethod
    def close_window(self, hwnd: int) -> WindowOperationResult:
        """Send normal close request (WM_CLOSE) to window."""
