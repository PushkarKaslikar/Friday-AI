"""Abstract interface defining Phase 6.2 InputEngine contracts."""

from abc import ABC, abstractmethod

from app.automation.input.models import (
    EasingProfile,
    InputResult,
    InputSource,
    InputTarget,
    MouseButton,
    TypingProfile,
)
from app.tools.execution.cancellation import CancellationToken


class IInputEngine(ABC):
    """Abstract interface for Windows mouse, keyboard, and human-like input control."""

    @abstractmethod
    def move_to(
        self,
        target: InputTarget,
        duration: float = 0.2,
        easing: EasingProfile = EasingProfile.SMOOTH,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Move mouse cursor smoothly to target location."""

    @abstractmethod
    def click(
        self,
        target: InputTarget | None = None,
        button: MouseButton = MouseButton.LEFT,
        click_count: int = 1,
        duration: float = 0.1,
        pause_before: float = 0.0,
        pause_after: float = 0.0,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Execute mouse click at target coordinates or current cursor position."""

    @abstractmethod
    def double_click(
        self,
        target: InputTarget | None = None,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Execute double left-click."""

    @abstractmethod
    def right_click(
        self,
        target: InputTarget | None = None,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Execute right-click."""

    @abstractmethod
    def middle_click(
        self,
        target: InputTarget | None = None,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Execute middle-click."""

    @abstractmethod
    def drag_and_drop(
        self,
        start_target: InputTarget,
        end_target: InputTarget,
        duration: float = 0.5,
        button: MouseButton = MouseButton.LEFT,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Execute drag and drop operation between start and end targets."""

    @abstractmethod
    def press_key(
        self,
        key: str,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Press single keyboard key."""

    @abstractmethod
    def press_hotkey(
        self,
        keys: list[str],
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Press key combination / hotkey."""

    @abstractmethod
    def type_text(
        self,
        text: str,
        profile: TypingProfile | str = TypingProfile.NORMAL,
        interval_ms: float | None = None,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Type text string with human-like timing profile."""

    @abstractmethod
    def release_all_inputs(self) -> None:
        """Emergency release of all held mouse buttons and modifier keys."""

    @abstractmethod
    def is_busy(self) -> bool:
        """Return True if an input sequence currently owns the input channel."""

    @abstractmethod
    def set_dry_run_mode(self, enabled: bool) -> None:
        """Enable or disable global dry-run mode."""
