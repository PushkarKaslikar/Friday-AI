"""UI State Manager maintaining reactive presentation state."""

from typing import Optional

from PySide6.QtCore import QObject, Signal


class UIStateManager(QObject):
    """Maintains UI application state decoupled from view widgets."""

    tab_changed = Signal(int, str)  # (index, tab_key)
    status_changed = Signal(str)  # status_message
    minimized_to_tray_changed = Signal(bool)

    _instance: Optional["UIStateManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        super().__init__()
        self._active_tab_index: int = 0
        self._active_tab_key: str = "home"
        self._status_message: str = "Ready"
        self._is_minimized_to_tray: bool = False
        self._initialized = True

    @property
    def active_tab_index(self) -> int:
        return self._active_tab_index

    @property
    def active_tab_key(self) -> str:
        return self._active_tab_key

    @property
    def status_message(self) -> str:
        return self._status_message

    @property
    def is_minimized_to_tray(self) -> bool:
        return self._is_minimized_to_tray

    def set_active_tab(self, index: int, key: str) -> None:
        """Set active navigation tab."""
        if self._active_tab_index != index or self._active_tab_key != key:
            self._active_tab_index = index
            self._active_tab_key = key
            self.tab_changed.emit(index, key)

    def set_status_message(self, message: str) -> None:
        """Update live UI status message."""
        if self._status_message != message:
            self._status_message = message
            self.status_changed.emit(message)

    def set_minimized_to_tray(self, minimized: bool) -> None:
        """Set minimized to tray state."""
        if self._is_minimized_to_tray != minimized:
            self._is_minimized_to_tray = minimized
            self.minimized_to_tray_changed.emit(minimized)
