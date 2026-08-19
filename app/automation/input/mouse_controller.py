"""Mouse movement, clicking, and drag-and-drop controller."""

import math
import time

from app.automation.input.errors import InputCancelledError
from app.automation.input.failsafe import InputFailsafe
from app.automation.input.interruption_monitor import InterruptionMonitor
from app.automation.input.models import (
    EasingProfile,
    InputSource,
    InputTarget,
    MouseButton,
    MousePosition,
)
from app.automation.input.native_input import NativeInputBackend
from app.automation.input.pyautogui_fallback import PyAutoGUIInputBackend
from app.automation.input.target_resolver import TargetResolver
from app.logging import logger
from app.tools.execution.cancellation import CancellationToken


class MouseController:
    """Controls mouse movement, easing interpolation, clicking, and drag-and-drop actions."""

    def __init__(
        self,
        native_backend: NativeInputBackend | None = None,
        pyautogui_backend: PyAutoGUIInputBackend | None = None,
        target_resolver: TargetResolver | None = None,
        failsafe: InputFailsafe | None = None,
        interruption_monitor: InterruptionMonitor | None = None,
    ) -> None:
        self.native_backend = native_backend or NativeInputBackend()
        self.pyautogui_backend = pyautogui_backend or PyAutoGUIInputBackend()
        self.target_resolver = target_resolver or TargetResolver()
        self.failsafe = failsafe or InputFailsafe()
        self.interruption_monitor = interruption_monitor or InterruptionMonitor()

    def _apply_easing(self, t: float, profile: EasingProfile) -> float:
        """Apply normalized easing function for parameter t in [0.0, 1.0]."""
        t = max(0.0, min(1.0, t))
        if profile == EasingProfile.LINEAR:
            return t
        elif profile == EasingProfile.EASE_IN_OUT:
            return 0.5 * (1.0 - math.cos(math.pi * t))
        elif profile == EasingProfile.SMOOTH:
            return t * t * (3.0 - 2.0 * t)
        return t

    def move_to(
        self,
        target: InputTarget,
        duration: float = 0.2,
        easing: EasingProfile = EasingProfile.SMOOTH,
        backend: InputSource = InputSource.NATIVE,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> MousePosition:
        """Execute smooth controlled mouse movement to target coordinates."""
        dest_pos = self.target_resolver.resolve_target(target)

        if dry_run:
            logger.debug(
                f"[DRY-RUN] Mouse move_to target ({dest_pos.x}, {dest_pos.y}) over {duration}s"
            )
            return dest_pos

        # Check safety before movement
        self.failsafe.check_failsafe()
        self.interruption_monitor.check_interruption()
        if cancellation_token and cancellation_token.is_cancelled:
            raise InputCancelledError(
                f"Mouse move cancelled: {cancellation_token.reason}"
            )

        if duration <= 0.01:
            if (
                backend == InputSource.PYAUTOGUI
                and self.pyautogui_backend.is_available()
            ):
                self.pyautogui_backend.move_to(dest_pos.x, dest_pos.y, duration=0.0)
            else:
                self.native_backend.move_to(dest_pos.x, dest_pos.y)
            self.interruption_monitor.update_expected_position(dest_pos.x, dest_pos.y)
            return dest_pos

        # Multi-step interpolated movement
        start_x, start_y = 0, 0
        if self.native_backend.is_available():
            try:
                import win32api

                start_x, start_y = win32api.GetCursorPos()
            except Exception:  # noqa: BLE001
                start_x, start_y = dest_pos.x, dest_pos.y

        steps = max(5, int(duration * 60))  # ~60 fps steps
        step_delay = duration / steps

        for step in range(1, steps + 1):
            if cancellation_token and cancellation_token.is_cancelled:
                raise InputCancelledError(
                    f"Mouse move cancelled: {cancellation_token.reason}"
                )

            self.failsafe.check_failsafe(is_automation_moving=True)
            self.interruption_monitor.check_interruption()

            progress = step / steps
            e_progress = self._apply_easing(progress, easing)

            curr_x = int(start_x + (dest_pos.x - start_x) * e_progress)
            curr_y = int(start_y + (dest_pos.y - start_y) * e_progress)

            if (
                backend == InputSource.PYAUTOGUI
                and self.pyautogui_backend.is_available()
            ):
                self.pyautogui_backend.move_to(curr_x, curr_y, duration=0.0)
            else:
                self.native_backend.move_to(curr_x, curr_y)

            self.interruption_monitor.update_expected_position(curr_x, curr_y)
            time.sleep(step_delay)

        return dest_pos

    def click(
        self,
        target: InputTarget | None = None,
        button: MouseButton = MouseButton.LEFT,
        click_count: int = 1,
        duration: float = 0.1,
        pause_before: float = 0.0,
        pause_after: float = 0.0,
        backend: InputSource = InputSource.NATIVE,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> MousePosition:
        """Execute mouse click at target coordinates."""
        if pause_before > 0:
            time.sleep(pause_before)

        if cancellation_token and cancellation_token.is_cancelled:
            raise InputCancelledError("Mouse click cancelled before action.")

        dest_pos: MousePosition
        if target is not None:
            dest_pos = self.move_to(
                target,
                duration=duration,
                backend=backend,
                dry_run=dry_run,
                cancellation_token=cancellation_token,
            )
        else:
            # Click at current cursor position
            if dry_run:
                dest_pos = MousePosition(x=0, y=0)
            else:
                try:
                    import win32api

                    cx, cy = win32api.GetCursorPos()
                    dest_pos = MousePosition(x=cx, y=cy)
                except Exception:
                    dest_pos = MousePosition(x=0, y=0)

        if dry_run:
            logger.debug(
                f"[DRY-RUN] Mouse {button.value} click (x{click_count}) at ({dest_pos.x}, {dest_pos.y})"
            )
            if pause_after > 0:
                time.sleep(pause_after)
            return dest_pos

        self.failsafe.check_failsafe()
        self.interruption_monitor.check_interruption()

        if backend == InputSource.PYAUTOGUI and self.pyautogui_backend.is_available():
            self.pyautogui_backend.click(
                x=dest_pos.x, y=dest_pos.y, button=button, click_count=click_count
            )
        else:
            self.native_backend.click(
                x=dest_pos.x, y=dest_pos.y, button=button, click_count=click_count
            )

        if pause_after > 0:
            time.sleep(pause_after)

        return dest_pos

    def drag_and_drop(
        self,
        start_target: InputTarget,
        end_target: InputTarget,
        duration: float = 0.5,
        button: MouseButton = MouseButton.LEFT,
        backend: InputSource = InputSource.NATIVE,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> tuple[MousePosition, MousePosition]:
        """Execute drag-and-drop operation from start to end coordinates."""
        start_pos = self.move_to(
            start_target,
            duration=0.1,
            backend=backend,
            dry_run=dry_run,
            cancellation_token=cancellation_token,
        )

        if dry_run:
            end_pos = self.target_resolver.resolve_target(end_target)
            logger.debug(
                f"[DRY-RUN] Drag from ({start_pos.x},{start_pos.y}) to ({end_pos.x},{end_pos.y})"
            )
            return start_pos, end_pos

        self.failsafe.check_failsafe()
        self.interruption_monitor.check_interruption()

        try:
            if (
                backend == InputSource.PYAUTOGUI
                and self.pyautogui_backend.is_available()
            ):
                self.pyautogui_backend.mouse_down(
                    start_pos.x, start_pos.y, button=button
                )
            else:
                self.native_backend.mouse_down(start_pos.x, start_pos.y, button=button)

            end_pos = self.move_to(
                end_target,
                duration=duration,
                easing=EasingProfile.EASE_IN_OUT,
                backend=backend,
                dry_run=dry_run,
                cancellation_token=cancellation_token,
            )
            return start_pos, end_pos
        finally:
            if not dry_run:
                try:
                    end_p = self.target_resolver.resolve_target(end_target)
                    if (
                        backend == InputSource.PYAUTOGUI
                        and self.pyautogui_backend.is_available()
                    ):
                        self.pyautogui_backend.mouse_up(end_p.x, end_p.y, button=button)
                    else:
                        self.native_backend.mouse_up(end_p.x, end_p.y, button=button)
                except Exception as exc:
                    logger.error(f"Failed mouse_up release in drag_and_drop: {exc}")
