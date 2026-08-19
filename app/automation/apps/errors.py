"""Custom exception hierarchy for Phase 6.4 Application Adapters."""


class AppAdapterError(Exception):
    """Base exception for all application adapter subsystem errors."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.cause = cause


class AppNotInstalledError(AppAdapterError):
    """Raised when an application is not installed on the host OS."""


class AppNotRunningError(AppAdapterError):
    """Raised when an action requires a running process but none is found."""


class AppAttachFailedError(AppAdapterError):
    """Raised when attaching to a running application window fails or is ambiguous."""


class AppLaunchFailedError(AppAdapterError):
    """Raised when launching an application process or waiting for readiness fails."""


class InvalidExecutableError(AppAdapterError):
    """Raised when an executable path or binary is invalid or disallowed."""


class InvalidWorkingDirectoryError(AppAdapterError):
    """Raised when a specified working directory does not exist or is inaccessible."""


class ExplorerNavigationFailedError(AppAdapterError):
    """Raised when File Explorer UI navigation fails or path is restricted."""


class TerminalNotAvailableError(AppAdapterError):
    """Raised when a target terminal type (CMD, PowerShell, WT) is not available."""
