"""Abstract base class for Application Adapters."""

from abc import ABC, abstractmethod
from typing import Any

from app.automation.apps.models import (
    ApplicationCapability,
    ApplicationIdentity,
    ApplicationLaunchResult,
    ApplicationState,
    AttachedApplication,
    LaunchRequest,
)
from app.automation.desktop.models import DesktopWindow


class ApplicationAdapter(ABC):
    """Abstract base class for all application-specific adapters."""

    @property
    @abstractmethod
    def identity(self) -> ApplicationIdentity:
        """Structured application identity metadata."""

    @property
    @abstractmethod
    def state(self) -> ApplicationState:
        """Current operational state of the adapter."""

    @property
    def capabilities(self) -> set[ApplicationCapability]:
        """Set of capabilities supported by this application adapter."""
        return self.identity.capabilities

    @abstractmethod
    def is_installed(self) -> bool:
        """Check if application binary exists on the host OS."""

    @abstractmethod
    def is_running(self) -> bool:
        """Check if at least one matching process is currently running."""

    @abstractmethod
    def find_windows(self) -> list[DesktopWindow]:
        """Find all active top-level windows matching this application."""

    @abstractmethod
    def attach(self, hwnd: int | None = None) -> AttachedApplication:
        """Attach adapter to a running instance or specific window HWND."""

    @abstractmethod
    def launch(self, request: LaunchRequest | None = None) -> ApplicationLaunchResult:
        """Launch application process and wait for window readiness."""

    @abstractmethod
    def get_active_window(self) -> DesktopWindow | None:
        """Retrieve the currently focused/active window for this application if any."""

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Perform non-invasive health check report for this adapter."""
