"""Abstract Service Interface and lifecycle state definitions for Friday AI Assistant."""

import time
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any


class ServiceState(Enum):
    """Service lifecycle states."""

    UNINITIALIZED = auto()
    INITIALIZING = auto()
    INITIALIZED = auto()
    STARTING = auto()
    RUNNING = auto()
    STOPPING = auto()
    STOPPED = auto()
    FAILED = auto()


class BaseService(ABC):
    """Abstract base class defining standardized service lifecycle contracts."""

    def __init__(self, name: str, is_critical: bool = False) -> None:
        self._name = name
        self._is_critical = is_critical
        self._state = ServiceState.UNINITIALIZED
        self._start_time: float | None = None
        self._failure_count: int = 0
        self._last_error: str | None = None

    @property
    def name(self) -> str:
        """Service identifier name."""
        return self._name

    @property
    def is_critical(self) -> bool:
        """Flag indicating if service failure is critical for application operation."""
        return self._is_critical

    @property
    def state(self) -> ServiceState:
        """Current service state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Cumulative count of service failures."""
        return self._failure_count

    @property
    def last_error(self) -> str | None:
        """Last error message recorded if failed."""
        return self._last_error

    @property
    def uptime_seconds(self) -> float:
        """Calculate active running uptime in seconds."""
        if self._state == ServiceState.RUNNING and self._start_time is not None:
            return round(time.time() - self._start_time, 2)
        return 0.0

    @abstractmethod
    def _do_initialize(self) -> None:
        """Internal initialization logic implemented by derived service."""

    @abstractmethod
    def _do_start(self) -> None:
        """Internal start logic implemented by derived service."""

    @abstractmethod
    def _do_stop(self) -> None:
        """Internal stop logic implemented by derived service."""

    def initialize(self) -> None:
        """Initialize service resources."""
        if self._state not in (
            ServiceState.UNINITIALIZED,
            ServiceState.STOPPED,
            ServiceState.FAILED,
        ):
            return

        self._state = ServiceState.INITIALIZING
        try:
            self._do_initialize()
            self._state = ServiceState.INITIALIZED
        except Exception as exc:
            self._state = ServiceState.FAILED
            self._failure_count += 1
            self._last_error = str(exc)
            raise

    def start(self) -> None:
        """Start background service execution."""
        if self._state == ServiceState.UNINITIALIZED:
            self.initialize()

        if self._state == ServiceState.RUNNING:
            return

        self._state = ServiceState.STARTING
        try:
            self._do_start()
            self._state = ServiceState.RUNNING
            self._start_time = time.time()
        except Exception as exc:
            self._state = ServiceState.FAILED
            self._failure_count += 1
            self._last_error = str(exc)
            raise

    def stop(self) -> None:
        """Stop background service execution."""
        if self._state not in (ServiceState.RUNNING, ServiceState.STARTING):
            return

        self._state = ServiceState.STOPPING
        try:
            self._do_stop()
            self._state = ServiceState.STOPPED
            self._start_time = None
        except Exception as exc:
            self._state = ServiceState.FAILED
            self._failure_count += 1
            self._last_error = str(exc)
            raise

    def restart(self) -> None:
        """Restart service execution cleanly."""
        self.stop()
        self.start()

    def shutdown(self) -> None:
        """Perform full shutdown and cleanup of service resources."""
        try:
            self.stop()
        finally:
            self._state = ServiceState.STOPPED

    def health_check(self) -> dict[str, Any]:
        """Collect service diagnostic health status payload."""
        return {
            "name": self.name,
            "state": self._state.name,
            "is_critical": self.is_critical,
            "uptime_seconds": self.uptime_seconds,
            "failure_count": self._failure_count,
            "last_error": self._last_error,
        }
