"""Main InputEngine service implementing IInputEngine interface."""

import threading
import time
import uuid
from typing import Any

from app.automation.input.diagnostics import InputDiagnostics
from app.automation.input.errors import (
    FailsafeAbortedError,
    InputCancelledError,
    InputInterruptedError,
    InputTimeoutError,
    InvalidCoordinatesError,
    InvalidTargetError,
)
from app.automation.input.failsafe import InputFailsafe
from app.automation.input.input_engine_interface import IInputEngine
from app.automation.input.interruption_monitor import InterruptionMonitor
from app.automation.input.keyboard_controller import KeyboardController
from app.automation.input.metrics import InputMetrics
from app.automation.input.models import (
    EasingProfile,
    InputResult,
    InputSource,
    InputStatus,
    InputTarget,
    MouseButton,
    TypingProfile,
)
from app.automation.input.mouse_controller import MouseController
from app.automation.input.native_input import NativeInputBackend
from app.automation.input.pyautogui_fallback import PyAutoGUIInputBackend
from app.automation.input.target_resolver import TargetResolver
from app.logging import logger
from app.tools.execution.cancellation import CancellationToken


class InputEngine(IInputEngine):
    """Main input control engine service managing mouse, keyboard, failsafe, and channel exclusivity."""

    def __init__(
        self,
        native_backend: NativeInputBackend | None = None,
        pyautogui_backend: PyAutoGUIInputBackend | None = None,
        target_resolver: TargetResolver | None = None,
        failsafe: InputFailsafe | None = None,
        interruption_monitor: InterruptionMonitor | None = None,
        metrics: InputMetrics | None = None,
        diagnostics: InputDiagnostics | None = None,
        default_backend: InputSource = InputSource.NATIVE,
        dry_run_mode: bool = False,
    ) -> None:
        self.native_backend = native_backend or NativeInputBackend()
        self.pyautogui_backend = pyautogui_backend or PyAutoGUIInputBackend()
        self.target_resolver = target_resolver or TargetResolver()
        self.metrics = metrics or InputMetrics()

        # Connect emergency release callback to backends
        self.failsafe = failsafe or InputFailsafe(
            release_callback=self.release_all_inputs
        )
        self.interruption_monitor = interruption_monitor or InterruptionMonitor(
            release_callback=self.release_all_inputs
        )
        self.diagnostics = diagnostics or InputDiagnostics(
            native_backend=self.native_backend,
            pyautogui_backend=self.pyautogui_backend,
            failsafe=self.failsafe,
            interruption_monitor=self.interruption_monitor,
        )

        self.mouse_controller = MouseController(
            native_backend=self.native_backend,
            pyautogui_backend=self.pyautogui_backend,
            target_resolver=self.target_resolver,
            failsafe=self.failsafe,
            interruption_monitor=self.interruption_monitor,
        )

        self.keyboard_controller = KeyboardController(
            native_backend=self.native_backend,
            pyautogui_backend=self.pyautogui_backend,
            failsafe=self.failsafe,
            interruption_monitor=self.interruption_monitor,
        )

        self.default_backend = default_backend
        self.dry_run_mode = dry_run_mode
        self._input_channel_lock = threading.Lock()
        self._active_operation_type: str | None = None

    def is_busy(self) -> bool:
        """Check if input channel is currently locked by an active input sequence."""
        return self._input_channel_lock.locked()

    def set_dry_run_mode(self, enabled: bool) -> None:
        """Enable or disable global dry-run mode."""
        self.dry_run_mode = enabled
        logger.info(f"InputEngine dry-run mode set to: {enabled}")

    def release_all_inputs(self) -> None:
        """Emergency release of all held mouse buttons and modifier keys."""
        try:
            self.native_backend.release_all_inputs()
        except Exception as exc:
            logger.error(f"Native backend release error: {exc}")

        try:
            self.pyautogui_backend.release_all_inputs()
        except Exception as exc:
            logger.error(f"PyAutoGUI backend release error: {exc}")

    def _select_backend(self, requested: InputSource | None) -> InputSource:
        """Select appropriate input backend based on request and availability."""
        if requested == InputSource.PYAUTOGUI and self.pyautogui_backend.is_available():
            return InputSource.PYAUTOGUI
        if self.native_backend.is_available():
            return InputSource.NATIVE
        if self.pyautogui_backend.is_available():
            return InputSource.PYAUTOGUI
        return InputSource.NATIVE

    def _execute_input_operation(
        self,
        op_type: str,
        func: Any,
        requested_backend: InputSource | None = None,
        dry_run: bool = False,
    ) -> InputResult:
        """Wrap input action execution with channel exclusivity, timing, safety, and error handling."""
        op_id = f"inop_{uuid.uuid4().hex[:12]}"
        effective_dry_run = dry_run or self.dry_run_mode
        effective_backend = self._select_backend(requested_backend)

        # Acquire input channel exclusivity lock
        acquired = self._input_channel_lock.acquire(blocking=False)
        if not acquired:
            logger.warning(f"InputEngine channel busy. Rejecting '{op_type}' request.")
            res = InputResult(
                status=InputStatus.INPUT_ENGINE_BUSY,
                operation_id=op_id,
                operation_type=op_type,
                backend=effective_backend,
                duration_ms=0.0,
                details={"error": "Input channel is locked by another operation."},
            )
            self.metrics.record_operation(
                op_type, res.status.value, effective_backend.value, 0.0
            )
            return res

        self._active_operation_type = op_type
        self.interruption_monitor.start_monitoring()
        t0 = time.perf_counter()

        status = InputStatus.COMPLETED
        interrupted = False
        cancelled = False
        failsafe_triggered = False
        details: dict[str, Any] = {}

        try:
            func(effective_backend, effective_dry_run)
        except InputCancelledError as exc:
            status = InputStatus.CANCELLED
            cancelled = True
            details["error"] = str(exc)
        except InputInterruptedError as exc:
            status = InputStatus.INTERRUPTED
            interrupted = True
            details["error"] = str(exc)
        except FailsafeAbortedError as exc:
            status = InputStatus.FAILSAFE_ABORTED
            failsafe_triggered = True
            details["error"] = str(exc)
        except (InvalidTargetError, InvalidCoordinatesError) as exc:
            status = InputStatus.INVALID_TARGET
            details["error"] = str(exc)
        except InputTimeoutError as exc:
            status = InputStatus.TIMEOUT
            details["error"] = str(exc)
        except Exception as exc:
            status = InputStatus.FAILED
            details["error"] = str(exc)
            logger.error(f"Input operation '{op_type}' failed: {exc}")
        finally:
            self.release_all_inputs()
            self.interruption_monitor.stop_monitoring()
            self._active_operation_type = None
            self._input_channel_lock.release()

        duration_ms = (time.perf_counter() - t0) * 1000.0
        result = InputResult(
            status=status,
            operation_id=op_id,
            operation_type=op_type,
            backend=effective_backend,
            duration_ms=round(duration_ms, 2),
            interrupted=interrupted,
            cancelled=cancelled,
            failsafe_triggered=failsafe_triggered,
            details=details,
        )
        self.metrics.record_operation(
            op_type,
            status.value,
            effective_backend.value,
            duration_ms,
            interrupted=interrupted,
            cancelled=cancelled,
            failsafe_triggered=failsafe_triggered,
        )
        return result

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

        def _action(b: InputSource, dr: bool) -> None:
            self.mouse_controller.move_to(
                target=target,
                duration=duration,
                easing=easing,
                backend=b,
                dry_run=dr,
                cancellation_token=cancellation_token,
            )

        return self._execute_input_operation(
            "move_to", _action, requested_backend=backend, dry_run=dry_run
        )

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

        def _action(b: InputSource, dr: bool) -> None:
            self.mouse_controller.click(
                target=target,
                button=button,
                click_count=click_count,
                duration=duration,
                pause_before=pause_before,
                pause_after=pause_after,
                backend=b,
                dry_run=dr,
                cancellation_token=cancellation_token,
            )

        return self._execute_input_operation(
            "click", _action, requested_backend=backend, dry_run=dry_run
        )

    def double_click(
        self,
        target: InputTarget | None = None,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Execute double left-click."""
        return self.click(
            target=target,
            button=MouseButton.LEFT,
            click_count=2,
            backend=backend,
            dry_run=dry_run,
            cancellation_token=cancellation_token,
        )

    def right_click(
        self,
        target: InputTarget | None = None,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Execute right-click."""
        return self.click(
            target=target,
            button=MouseButton.RIGHT,
            click_count=1,
            backend=backend,
            dry_run=dry_run,
            cancellation_token=cancellation_token,
        )

    def middle_click(
        self,
        target: InputTarget | None = None,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Execute middle-click."""
        return self.click(
            target=target,
            button=MouseButton.MIDDLE,
            click_count=1,
            backend=backend,
            dry_run=dry_run,
            cancellation_token=cancellation_token,
        )

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

        def _action(b: InputSource, dr: bool) -> None:
            self.mouse_controller.drag_and_drop(
                start_target=start_target,
                end_target=end_target,
                duration=duration,
                button=button,
                backend=b,
                dry_run=dr,
                cancellation_token=cancellation_token,
            )

        return self._execute_input_operation(
            "drag_and_drop", _action, requested_backend=backend, dry_run=dry_run
        )

    def press_key(
        self,
        key: str,
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Press single keyboard key."""

        def _action(b: InputSource, dr: bool) -> None:
            self.keyboard_controller.press_key(
                key_name=key,
                backend=b,
                dry_run=dr,
                cancellation_token=cancellation_token,
            )

        return self._execute_input_operation(
            "press_key", _action, requested_backend=backend, dry_run=dry_run
        )

    def press_hotkey(
        self,
        keys: list[str],
        backend: InputSource | None = None,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> InputResult:
        """Press key combination / hotkey."""

        def _action(b: InputSource, dr: bool) -> None:
            self.keyboard_controller.press_hotkey(
                keys=keys, backend=b, dry_run=dr, cancellation_token=cancellation_token
            )

        return self._execute_input_operation(
            "press_hotkey", _action, requested_backend=backend, dry_run=dry_run
        )

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

        def _action(b: InputSource, dr: bool) -> None:
            self.keyboard_controller.type_text(
                text=text,
                profile=profile,
                interval_ms=interval_ms,
                backend=b,
                dry_run=dr,
                cancellation_token=cancellation_token,
            )

        return self._execute_input_operation(
            "type_text", _action, requested_backend=backend, dry_run=dry_run
        )
