"""Window Manager tracking and controlling window instances and lifecycle."""

from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget

from app.logging import logger


class WindowManager(QObject):
    """Centralized window manager responsible for opening, focusing, and destroying windows."""

    window_opened = Signal(str)  # Emits window key when opened
    window_closed = Signal(str)  # Emits window key when closed

    _instance: Optional["WindowManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        super().__init__()
        self._active_windows: dict[str, QWidget] = {}
        self._initialized = True

    def register_window(self, key: str, window: QWidget) -> None:
        """Register a window instance with a unique key.

        Args:
            key: Window identifier key (e.g. 'main', 'settings', 'splash').
            window: QWidget or QMainWindow instance.
        """
        self._active_windows[key] = window
        logger.info(
            f"Window registered: '{key}'. Total active windows: {len(self._active_windows)}"
        )
        self.window_opened.emit(key)

    def get_window(self, key: str) -> QWidget | None:
        """Get window instance by key if registered."""
        return self._active_windows.get(key)

    def is_window_open(self, key: str) -> bool:
        """Check if a window with the given key exists and is visible."""
        win = self.get_window(key)
        return win is not None and win.isVisible()

    def show_window(self, key: str) -> bool:
        """Show and bring window to front if registered.

        Returns:
            bool: True if window exists and was shown.
        """
        win = self.get_window(key)
        if win is None:
            logger.warning(f"Attempted to show unregistered window: '{key}'.")
            return False

        if win.isMinimized():
            win.showNormal()
        win.show()
        win.raise_()
        win.activateWindow()
        logger.info(f"Window focused: '{key}'.")
        return True

    def hide_window(self, key: str) -> bool:
        """Hide window if registered."""
        win = self.get_window(key)
        if win is not None:
            win.hide()
            logger.info(f"Window hidden: '{key}'.")
            return True
        return False

    def close_window(self, key: str) -> bool:
        """Close and unregister a window instance."""
        win = self._active_windows.pop(key, None)
        if win is not None:
            win.close()
            logger.info(f"Window closed: '{key}'.")
            self.window_closed.emit(key)
            return True
        return False

    def close_all(self) -> None:
        """Close all registered active windows."""
        keys = list(self._active_windows.keys())
        for k in keys:
            self.close_window(k)
