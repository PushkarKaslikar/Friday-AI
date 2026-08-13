"""Navigation Manager controlling page switching and navigation signals."""

from typing import Optional

from PySide6.QtCore import QObject, Signal


class NavigationManager(QObject):
    """Manages active page index, route keys, and navigation state changes."""

    page_changed = Signal(int, str)  # (page_index, page_key)

    _instance: Optional["NavigationManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        super().__init__()
        self._routes: list[str] = [
            "home",
            "assistant",
            "memory",
            "automation",
            "plugins",
            "logs",
            "diagnostics",
        ]
        self._current_index: int = 0
        self._initialized = True

    @property
    def current_index(self) -> int:
        return self._current_index

    @property
    def current_key(self) -> str:
        if 0 <= self._current_index < len(self._routes):
            return self._routes[self._current_index]
        return "home"

    def navigate_to_index(self, index: int) -> None:
        """Navigate to specific page index."""
        if 0 <= index < len(self._routes) and index != self._current_index:
            self._current_index = index
            self.page_changed.emit(self._current_index, self._routes[index])

    def navigate_to_key(self, key: str) -> None:
        """Navigate to specific page by route key."""
        if key in self._routes:
            idx = self._routes.index(key)
            self.navigate_to_index(idx)
