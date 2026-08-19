"""Domain models for Phase 6.4 Application Control & Interaction Adapters."""

import time
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ApplicationState(str, Enum):
    """Lifecycle states of an application adapter or process instance."""

    NOT_INSTALLED = "NOT_INSTALLED"
    INSTALLED = "INSTALLED"
    NOT_RUNNING = "NOT_RUNNING"
    RUNNING = "RUNNING"
    ATTACHED = "ATTACHED"
    LAUNCHING = "LAUNCHING"
    READY = "READY"
    FAILED = "FAILED"


class ApplicationCapability(str, Enum):
    """Capabilities supported by application adapters."""

    LAUNCH = "LAUNCH"
    ATTACH = "ATTACH"
    FOCUS = "FOCUS"
    NAVIGATION = "NAVIGATION"
    ITEM_SELECTION = "ITEM_SELECTION"
    ITEM_OPEN = "ITEM_OPEN"
    CREATE_FOLDER = "CREATE_FOLDER"
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    WORKING_DIRECTORY = "WORKING_DIRECTORY"


class TerminalType(str, Enum):
    """Supported terminal applications."""

    CMD = "CMD"
    POWERSHELL = "POWERSHELL"
    WINDOWS_TERMINAL = "WINDOWS_TERMINAL"
    PWSH = "PWSH"


class ApplicationIdentity(BaseModel):
    """Structured identity for an application."""

    app_id: str = Field(
        description="Unique application identifier (e.g. 'explorer', 'terminal')"
    )
    display_name: str = Field(description="Human-readable application name")
    executable_names: list[str] = Field(
        default_factory=list, description="Primary executable binary names"
    )
    aliases: list[str] = Field(
        default_factory=list, description="Supported search aliases"
    )
    process_names: list[str] = Field(
        default_factory=list, description="Matching process names in Task Manager"
    )
    known_paths: list[str] = Field(
        default_factory=list, description="Known installation file paths"
    )
    capabilities: set[ApplicationCapability] = Field(
        default_factory=set, description="Supported operations"
    )


class AttachedApplication(BaseModel):
    """Active process/window attachment state."""

    app_identity: ApplicationIdentity
    process_id: int = Field(default=0, description="Process ID (PID)")
    hwnd: int = Field(default=0, description="Top-level window handle (HWND)")
    window_title: str = Field(default="", description="Active window title")
    attached_at: float = Field(
        default_factory=time.time, description="Timestamp of attachment"
    )
    state: ApplicationState = Field(
        default=ApplicationState.ATTACHED, description="Attachment state"
    )
    capabilities: set[ApplicationCapability] = Field(
        default_factory=set, description="Active capabilities"
    )


class LaunchRequest(BaseModel):
    """Structured application launch request."""

    application: str = Field(
        description="Target application alias, app_id, or display name"
    )
    executable: str | None = Field(
        default=None, description="Optional explicit executable path"
    )
    arguments: list[str] = Field(
        default_factory=list, description="Validated command argument list"
    )
    working_directory: str | None = Field(
        default=None, description="Target working directory"
    )
    environment_overrides: dict[str, str] = Field(
        default_factory=dict, description="Environment variables"
    )
    wait_for_ready: bool = Field(
        default=True, description="Wait for process and window readiness"
    )
    timeout: float = Field(
        default=10.0, ge=0.5, le=60.0, description="Readiness timeout in seconds"
    )
    focus_after_launch: bool = Field(
        default=True, description="Focus the window after launch"
    )


class ApplicationLaunchResult(BaseModel):
    """Result payload for application launch operations."""

    status: str = Field(
        description="Launch status (SUCCESS, FAILED, INVALID_PATH, TIMEOUT, etc.)"
    )
    app_id: str = Field(default="", description="Application identifier")
    process_id: int = Field(default=0, description="Spawned process ID")
    hwnd: int = Field(default=0, description="Resolved window handle")
    state: ApplicationState = Field(
        default=ApplicationState.NOT_RUNNING, description="Resulting application state"
    )
    duration_ms: float = Field(
        default=0.0, description="Execution duration in milliseconds"
    )
    reason: str = Field(default="", description="Description or error reason")
    attached: AttachedApplication | None = Field(
        default=None, description="Attached application object if successful"
    )


class AdapterOperationResult(BaseModel):
    """Generic operation result from an application adapter."""

    status: str = Field(
        description="Operation status (SUCCESS, PARTIAL, FAILED, UIA_UNAVAILABLE, TIMEOUT, etc.)"
    )
    message: str = Field(default="", description="Operation status description")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional context metadata"
    )


class ExplorerOperationResult(BaseModel):
    """Result payload for File Explorer operations."""

    status: str = Field(
        description="Status (SUCCESS, NAVIGATION_FAILED, ITEM_NOT_FOUND, FAILED)"
    )
    current_path: str | None = Field(
        default=None, description="Current Explorer folder path"
    )
    target_path: str | None = Field(
        default=None, description="Intended target folder path"
    )
    selected_items: list[str] = Field(
        default_factory=list, description="Currently selected file/folder names"
    )
    visible_items: list[str] = Field(
        default_factory=list, description="Visible items in folder view"
    )
    window_title: str = Field(default="", description="Explorer window title")
    hwnd: int = Field(default=0, description="Explorer HWND handle")
    message: str = Field(
        default="", description="Operation description or error message"
    )


class TerminalOutput(BaseModel):
    """Bounded text output captured from a terminal buffer or output stream."""

    terminal_type: TerminalType = Field(description="Type of terminal")
    process_id: int = Field(default=0, description="Process ID")
    text: str = Field(default="", description="Sanitized text output")
    timestamp: float = Field(default_factory=time.time, description="Capture timestamp")
    is_complete: bool = Field(
        default=True, description="Whether buffer reading reached end"
    )
    source: str = Field(
        default="UIA_TEXT_BUFFER", description="Output source mechanism"
    )


class TerminalOperationResult(BaseModel):
    """Result payload for Terminal operations."""

    status: str = Field(
        description="Status (SUCCESS, ATTACH_FAILED, INPUT_FAILED, TIMEOUT, FAILED)"
    )
    terminal_type: TerminalType | None = Field(
        default=None, description="Target terminal type"
    )
    process_id: int = Field(default=0, description="Terminal PID")
    hwnd: int = Field(default=0, description="Terminal HWND")
    working_directory: str | None = Field(
        default=None, description="Current working directory"
    )
    output: TerminalOutput | None = Field(
        default=None, description="Captured terminal output buffer if available"
    )
    output_available: bool = Field(
        default=False, description="Whether text buffer output was reliably captured"
    )
    message: str = Field(default="", description="Status description or error details")
