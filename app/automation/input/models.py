"""Domain models for Phase 6.2 Mouse, Keyboard & Human-Like Input Control Engine."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.automation.models import AutomationElement


class MouseButton(str, Enum):
    """Mouse button identifiers."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    MIDDLE = "MIDDLE"


class EasingProfile(str, Enum):
    """Mouse movement interpolation profiles."""

    LINEAR = "LINEAR"
    EASE_IN_OUT = "EASE_IN_OUT"
    SMOOTH = "SMOOTH"


class TypingProfile(str, Enum):
    """Human-like text typing speed profiles."""

    INSTANT = "INSTANT"  # 0ms interval
    FAST = "FAST"  # 20ms interval
    NORMAL = "NORMAL"  # 50ms interval
    SLOW = "SLOW"  # 120ms interval


def get_typing_interval_seconds(profile: TypingProfile | str) -> float:
    """Return character delay in seconds for typing profile."""
    prof_str = (
        profile.value if isinstance(profile, TypingProfile) else str(profile).upper()
    )
    if prof_str == TypingProfile.INSTANT.value:
        return 0.0
    elif prof_str == TypingProfile.FAST.value:
        return 0.02
    elif prof_str == TypingProfile.SLOW.value:
        return 0.12
    return 0.05  # NORMAL default


class InputSource(str, Enum):
    """Input execution backend identifiers."""

    NATIVE = "NATIVE"
    PYAUTOGUI = "PYAUTOGUI"


class TargetType(str, Enum):
    """Input target classifications."""

    SCREEN_COORDINATE = "SCREEN_COORDINATE"
    UIA_ELEMENT = "UIA_ELEMENT"
    WINDOW = "WINDOW"


class InputStatus(str, Enum):
    """Execution status for input operations."""

    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"
    FAILED = "FAILED"
    INVALID_TARGET = "INVALID_TARGET"
    TIMEOUT = "TIMEOUT"
    FAILSAFE_ABORTED = "FAILSAFE_ABORTED"
    INPUT_ENGINE_BUSY = "INPUT_ENGINE_BUSY"


class MousePosition(BaseModel):
    """2D screen coordinate position."""

    x: int = Field(..., description="Screen X coordinate")
    y: int = Field(..., description="Screen Y coordinate")


class InputTarget(BaseModel):
    """Target representation for an input action."""

    target_type: TargetType = Field(default=TargetType.SCREEN_COORDINATE)
    x: int | None = Field(
        default=None,
        description="Screen X coordinate if target_type is SCREEN_COORDINATE",
    )
    y: int | None = Field(
        default=None,
        description="Screen Y coordinate if target_type is SCREEN_COORDINATE",
    )
    element: AutomationElement | None = Field(
        default=None, description="Target UIA element if target_type is UIA_ELEMENT"
    )
    window_handle: int | None = Field(
        default=None, description="Target HWND window handle if target_type is WINDOW"
    )


class MouseAction(BaseModel):
    """Payload options for mouse operations."""

    target: InputTarget | None = None
    button: MouseButton = Field(default=MouseButton.LEFT)
    click_count: int = Field(default=1, ge=1, le=5)
    duration: float = Field(
        default=0.2, ge=0.0, le=10.0, description="Movement duration in seconds"
    )
    pause_before: float = Field(default=0.0, ge=0.0, le=5.0)
    pause_after: float = Field(default=0.0, ge=0.0, le=5.0)
    easing: EasingProfile = Field(default=EasingProfile.SMOOTH)


class KeyboardAction(BaseModel):
    """Payload options for keyboard operations."""

    action_type: str = Field(
        ..., description="Action category (press, down, up, hotkey, typing)"
    )
    key: str | None = Field(
        default=None, description="Key name or virtual key identifier"
    )
    keys: list[str] = Field(
        default_factory=list, description="Sequence of keys for combination or hotkey"
    )
    text: str | None = Field(default=None, description="Text string to type")
    typing_profile: TypingProfile = Field(default=TypingProfile.NORMAL)
    interval_ms: float | None = Field(
        default=None, description="Custom character interval override in ms"
    )


class InputResult(BaseModel):
    """Structured result returned by input engine operations."""

    status: InputStatus
    operation_id: str = Field(..., description="Unique operation identifier")
    operation_type: str = Field(
        ..., description="Name of operation (move_to, click, type_text, hotkey, etc.)"
    )
    backend: InputSource = Field(default=InputSource.NATIVE)
    duration_ms: float = Field(
        default=0.0, description="Total execution time in milliseconds"
    )
    interrupted: bool = Field(
        default=False,
        description="True if user physical activity interrupted operation",
    )
    cancelled: bool = Field(
        default=False, description="True if cancellation token was triggered"
    )
    failsafe_triggered: bool = Field(
        default=False, description="True if emergency corner failsafe aborted operation"
    )
    details: dict[str, Any] = Field(
        default_factory=dict, description="Diagnostic operation metadata"
    )
