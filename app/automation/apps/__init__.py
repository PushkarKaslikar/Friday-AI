"""Phase 6.4 Application Control & Interaction Adapters package."""

from app.automation.apps.errors import (
    AppAdapterError,
    AppAttachFailedError,
    AppLaunchFailedError,
    AppNotInstalledError,
    AppNotRunningError,
    ExplorerNavigationFailedError,
    InvalidExecutableError,
    InvalidWorkingDirectoryError,
    TerminalNotAvailableError,
)
from app.automation.apps.models import (
    AdapterOperationResult,
    ApplicationCapability,
    ApplicationIdentity,
    ApplicationLaunchResult,
    ApplicationState,
    AttachedApplication,
    ExplorerOperationResult,
    LaunchRequest,
    TerminalOperationResult,
    TerminalOutput,
    TerminalType,
)

__all__ = [
    "AdapterOperationResult",
    "AppAdapterError",
    "AppAttachFailedError",
    "AppLaunchFailedError",
    "AppNotInstalledError",
    "AppNotRunningError",
    "ApplicationCapability",
    "ApplicationIdentity",
    "ApplicationLaunchResult",
    "ApplicationState",
    "AttachedApplication",
    "ExplorerNavigationFailedError",
    "ExplorerOperationResult",
    "InvalidExecutableError",
    "InvalidWorkingDirectoryError",
    "LaunchRequest",
    "TerminalNotAvailableError",
    "TerminalOperationResult",
    "TerminalOutput",
    "TerminalType",
]
