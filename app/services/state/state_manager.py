"""Application State Manager tracking system-wide runtime states."""

import threading
from enum import Enum, auto
from typing import Optional

from app.logging import logger


class ApplicationState(Enum):
    """Global Application Runtime States."""

    STARTUP = auto()
    RUNNING = auto()
    MINIMIZED = auto()
    SHUTTING_DOWN = auto()
    STOPPED = auto()


class AppStateManager:
    """Centralized manager for tracking application runtime state."""

    _instance: Optional["AppStateManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._lock = threading.RLock()
        self._current_state = ApplicationState.STARTUP
        self._initialized = True

    @property
    def current_state(self) -> ApplicationState:
        """Get current global application state."""
        with self._lock:
            return self._current_state

    def set_state(self, new_state: ApplicationState) -> None:
        """Update current application state.

        Args:
            new_state: New ApplicationState enum value.
        """
        with self._lock:
            if self._current_state != new_state:
                old_state = self._current_state
                self._current_state = new_state
                logger.info(
                    f"AppStateManager: State transitioned from {old_state.name} -> {new_state.name}."
                )
