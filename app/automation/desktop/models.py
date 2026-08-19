"""Domain models for Phase 6.3 Window Management, Desktop Control, Clipboard & Screen Inspection Engine."""

import time
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class WindowState(str, Enum):
    """Window display state classifications."""

    ACTIVE = "ACTIVE"
    VISIBLE = "VISIBLE"
    MINIMIZED = "MINIMIZED"
    MAXIMIZED = "MAXIMIZED"
    RESTORED = "RESTORED"
    CLOSED = "CLOSED"
    HIDDEN = "HIDDEN"


class SnapPosition(str, Enum):
    """Monitor work area window snap position targets."""

    LEFT = "LEFT"  # Left 50%
    RIGHT = "RIGHT"  # Right 50%
    TOP = "TOP"  # Top 50%
    BOTTOM = "BOTTOM"  # Bottom 50%
    TOP_LEFT = "TOP_LEFT"  # Top-left quadrant 25%
    TOP_RIGHT = "TOP_RIGHT"  # Top-right quadrant 25%
    BOTTOM_LEFT = "BOTTOM_LEFT"  # Bottom-left quadrant 25%
    BOTTOM_RIGHT = "BOTTOM_RIGHT"  # Bottom-right quadrant 25%
    CENTER = "CENTER"  # Centered window
    FULLSCREEN = "FULLSCREEN"  # Maximize to work area


class ClipboardFormat(str, Enum):
    """Supported Windows clipboard format classifications."""

    TEXT = "TEXT"
    UNICODE_TEXT = "UNICODE_TEXT"
    HTML = "HTML"
    FILE_LIST = "FILE_LIST"
    EMPTY = "EMPTY"
    UNSUPPORTED = "UNSUPPORTED"


class DesktopWindow(BaseModel):
    """Detailed domain model representing a Windows top-level window."""

    hwnd: int = Field(..., description="Native HWND window handle")
    title: str = Field(default="", description="Window title text")
    process_id: int = Field(default=0, description="Process ID owning the window")
    process_name: str = Field(
        default="", description="Executable name owning the window"
    )
    class_name: str = Field(default="", description="Win32 window class name")
    is_visible: bool = Field(
        default=True, description="True if window is visible on desktop"
    )
    is_minimized: bool = Field(default=False, description="True if window is minimized")
    is_maximized: bool = Field(default=False, description="True if window is maximized")
    is_active: bool = Field(
        default=False, description="True if window is currently foreground active"
    )
    left: int = Field(default=0, description="Screen X left position")
    top: int = Field(default=0, description="Screen Y top position")
    right: int = Field(default=0, description="Screen X right position")
    bottom: int = Field(default=0, description="Screen Y bottom position")
    width: int = Field(default=0, description="Window width in pixels")
    height: int = Field(default=0, description="Window height in pixels")
    monitor_id: int = Field(default=0, description="Assigned monitor ID")
    z_order: int = Field(default=0, description="Relative Z-order index")
    framework_id: str = Field(
        default="", description="UI Automation framework ID if available"
    )


class MonitorInfo(BaseModel):
    """Information payload representing a physical monitor display."""

    monitor_id: int = Field(..., description="Monitor identifier index")
    is_primary: bool = Field(
        default=False, description="True if primary display monitor"
    )
    x: int = Field(default=0, description="Virtual screen origin X")
    y: int = Field(default=0, description="Virtual screen origin Y")
    width: int = Field(default=1920, description="Monitor pixel width")
    height: int = Field(default=1080, description="Monitor pixel height")
    work_left: int = Field(default=0, description="Work area left (excluding taskbar)")
    work_top: int = Field(default=0, description="Work area top")
    work_right: int = Field(default=1920, description="Work area right")
    work_bottom: int = Field(default=1080, description="Work area bottom")
    scale_factor: float = Field(default=1.0, description="DPI scale factor estimate")


class VirtualDesktopInfo(BaseModel):
    """Payload representing Windows virtual desktop status."""

    is_available: bool = Field(
        default=False, description="True if virtual desktop APIs are supported"
    )
    current_desktop_id: str | None = Field(
        default=None, description="Active virtual desktop GUID"
    )
    total_desktops: int = Field(default=1, description="Total virtual desktop count")
    is_window_on_current: bool = Field(
        default=True, description="True if query target is on current desktop"
    )


class WindowLayoutEntry(BaseModel):
    """Single window entry recorded in a WorkspaceLayout snapshot."""

    hwnd: int
    title: str
    process_name: str
    class_name: str
    state: WindowState = WindowState.RESTORED
    left: int
    top: int
    width: int
    height: int
    monitor_id: int = 0


class WorkspaceLayout(BaseModel):
    """Persistent representation of a saved desktop workspace layout."""

    layout_id: str = Field(default_factory=lambda: f"ws_{uuid.uuid4().hex[:12]}")
    created_at: float = Field(default_factory=time.time)
    monitors: list[MonitorInfo] = Field(default_factory=list)
    windows: list[WindowLayoutEntry] = Field(default_factory=list)


class ScreenCaptureResult(BaseModel):
    """Result container for in-memory screen capture operations."""

    status: str = Field(default="COMPLETED")
    image_bytes: bytes | None = Field(
        default=None, exclude=True, description="Raw PNG/JPEG byte content in-memory"
    )
    width: int = Field(default=0)
    height: int = Field(default=0)
    monitor_id: int | None = Field(default=None)
    region: tuple[int, int, int, int] | None = Field(default=None)
    timestamp: float = Field(default_factory=time.time)
    duration_ms: float = Field(default=0.0)


class ClipboardResult(BaseModel):
    """Result container for clipboard read and write operations."""

    status: str = Field(default="COMPLETED")
    format: ClipboardFormat = Field(default=ClipboardFormat.TEXT)
    text: str | None = Field(
        default=None, description="Sanitized clipboard text content"
    )
    html: str | None = Field(
        default=None, description="Sanitized clipboard HTML content"
    )
    file_paths: list[str] = Field(
        default_factory=list, description="File paths if CF_HDROP format"
    )
    is_masked: bool = Field(
        default=False, description="True if sensitive secrets were masked"
    )
    size_bytes: int = Field(default=0)


class WindowOperationResult(BaseModel):
    """Result payload returned by window control operations."""

    status: str = Field(default="COMPLETED")
    hwnd: int = Field(..., description="Target HWND window handle")
    operation: str = Field(
        ..., description="Operation name (focus, move, resize, snap, etc.)"
    )
    previous_geometry: dict[str, int] | None = Field(default=None)
    new_geometry: dict[str, int] | None = Field(default=None)
    monitor_id: int | None = Field(default=None)
    reason_code: str = Field(default="SUCCESS")
    duration_ms: float = Field(default=0.0)


class DesktopSnapshot(BaseModel):
    """Aggregated snapshot of current desktop state."""

    active_window: DesktopWindow | None = Field(default=None)
    windows: list[DesktopWindow] = Field(default_factory=list)
    monitors: list[MonitorInfo] = Field(default_factory=list)
    virtual_desktop: VirtualDesktopInfo = Field(default_factory=VirtualDesktopInfo)
    clipboard_format: ClipboardFormat = Field(default=ClipboardFormat.EMPTY)
    timestamp: float = Field(default_factory=time.time)
