"""Physical top-left screen corner emergency failsafe detector."""

import sys
from collections.abc import Callable

from app.automation.input.errors import FailsafeAbortedError
from app.logging import logger

try:
    import win32api

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class InputFailsafe:
    """Monitors mouse cursor position for emergency top-left screen corner abort condition."""

    def __init__(
        self,
        enabled: bool = True,
        corner_threshold: int = 10,
        release_callback: Callable[[], None] | None = None,
    ) -> None:
        self.enabled = enabled
        self.corner_threshold = corner_threshold
        self.release_callback = release_callback

    def check_failsafe(
        self,
        is_automation_moving: bool = False,
        pos_override: tuple[int, int] | None = None,
    ) -> None:
        """Inspect cursor position and trigger emergency abort if physical mouse is in top-left corner."""
        if not self.enabled or is_automation_moving:
            return

        x, y = -1, -1
        if pos_override is not None:
            x, y = pos_override
        elif sys.platform == "win32" and PYWIN32_AVAILABLE:
            try:
                x, y = win32api.GetCursorPos()
            except Exception as exc:
                logger.debug(f"Failsafe position query error: {exc}")
                return
        else:
            return

        if 0 <= x <= self.corner_threshold and 0 <= y <= self.corner_threshold:
            logger.critical(
                f"Emergency Input Failsafe Triggered! Cursor detected in top-left corner ({x},{y}). Aborting automation."
            )
            if self.release_callback:
                try:
                    self.release_callback()
                except Exception as exc:
                    logger.error(f"Failsafe release callback error: {exc}")

            raise FailsafeAbortedError(
                f"Emergency physical failsafe activated at corner ({x}, {y}).",
                details={"x": x, "y": y, "threshold": self.corner_threshold},
            )
