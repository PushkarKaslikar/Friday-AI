"""Structured typed event model hierarchy for decoupled communication."""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    """Base event model for all system and service messages."""

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    sender: str = "system"
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """Return event type name."""
        return self.__class__.__name__


# Application Lifecycle Events
@dataclass
class ApplicationStarted(Event):
    app_name: str = ""
    version: str = ""
    environment: str = ""


@dataclass
class ApplicationStopped(Event):
    app_name: str = ""
    reason: str = "normal"


# UI & Window Events
@dataclass
class WindowOpened(Event):
    window_key: str = ""


@dataclass
class WindowClosed(Event):
    window_key: str = ""


@dataclass
class ThemeChanged(Event):
    theme_name: str = ""


@dataclass
class SettingsChanged(Event):
    changed_keys: list[str] = field(default_factory=list)


# Service Lifecycle Events
@dataclass
class ServiceStarted(Event):
    service_name: str = ""


@dataclass
class ServiceStopped(Event):
    service_name: str = ""


@dataclass
class ServiceFailed(Event):
    service_name: str = ""
    error_message: str = ""


# Health Monitoring Events
@dataclass
class HealthWarning(Event):
    service_name: str = ""
    warning_message: str = ""


@dataclass
class HealthRecovered(Event):
    service_name: str = ""


# Task Execution Events
@dataclass
class TaskStarted(Event):
    task_id: str = ""
    task_name: str = ""


@dataclass
class TaskCompleted(Event):
    task_id: str = ""
    result_data: dict[str, Any] | None = None


@dataclass
class TaskFailed(Event):
    task_id: str = ""
    error_message: str = ""
