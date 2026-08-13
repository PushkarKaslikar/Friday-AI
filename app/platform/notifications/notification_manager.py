"""Windows Native Notification Manager handling system toast notifications and history."""

import datetime
from enum import Enum, auto
from typing import Any, Optional

from app.logging import logger
from app.services.events.event_bus import EventBus
from app.ui.managers.tray_manager import TrayManager


class NotificationLevel(Enum):
    """Notification level types."""

    INFO = auto()
    SUCCESS = auto()
    WARNING = auto()
    ERROR = auto()
    PROGRESS = auto()


class NotificationManager:
    """Centralized manager dispatching native Windows toast notifications."""

    _instance: Optional["NotificationManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        tray_manager: TrayManager | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        if getattr(self, "_initialized", False):
            return

        self.tray_manager = tray_manager
        self.event_bus = event_bus or EventBus()
        self._history: list[dict[str, Any]] = []
        self._initialized = True

    def show_notification(
        self,
        title: str,
        message: str,
        level: NotificationLevel = NotificationLevel.INFO,
        duration_ms: int = 4000,
    ) -> None:
        """Display native Windows toast notification.

        Args:
            title: Notification title.
            message: Notification body text.
            level: NotificationLevel enum value.
            duration_ms: Display duration in milliseconds.
        """
        now_str = str(datetime.datetime.now())  # noqa: DTZ005
        record = {
            "title": title,
            "message": message,
            "level": level.name,
            "timestamp": now_str,
        }
        self._history.append(record)

        logger.info(f"Notification [{level.name}]: {title} - {message}")

        if self.tray_manager:
            try:
                self.tray_manager.show_notification(title, message, duration_ms)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"NotificationManager: Failed to emit tray toast: {exc}")

    def show_info(self, title: str, message: str) -> None:
        """Show Info notification."""
        self.show_notification(title, message, NotificationLevel.INFO)

    def show_success(self, title: str, message: str) -> None:
        """Show Success notification."""
        self.show_notification(title, message, NotificationLevel.SUCCESS)

    def show_warning(self, title: str, message: str) -> None:
        """Show Warning notification."""
        self.show_notification(title, message, NotificationLevel.WARNING)

    def show_error(self, title: str, message: str) -> None:
        """Show Error notification."""
        self.show_notification(title, message, NotificationLevel.ERROR)

    def get_history(self) -> list[dict[str, Any]]:
        """Get copy of notification history records."""
        return list(self._history)

    def clear_history(self) -> None:
        """Clear notification history records."""
        self._history.clear()
