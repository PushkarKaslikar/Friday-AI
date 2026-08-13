"""Events package."""

from app.services.events.event_bus import EventBus
from app.services.events.event_models import (
    ApplicationStarted,
    ApplicationStopped,
    Event,
    HealthRecovered,
    HealthWarning,
    ServiceFailed,
    ServiceStarted,
    ServiceStopped,
    SettingsChanged,
    TaskCompleted,
    TaskFailed,
    TaskStarted,
    ThemeChanged,
    WindowClosed,
    WindowOpened,
)

__all__ = [
    "ApplicationStarted",
    "ApplicationStopped",
    "Event",
    "EventBus",
    "HealthRecovered",
    "HealthWarning",
    "ServiceFailed",
    "ServiceStarted",
    "ServiceStopped",
    "SettingsChanged",
    "TaskCompleted",
    "TaskFailed",
    "TaskStarted",
    "ThemeChanged",
    "WindowClosed",
    "WindowOpened",
]
