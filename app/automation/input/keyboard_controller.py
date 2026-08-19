"""Keyboard input, hotkey combinations, and human-like typing controller."""

import time

from app.automation.input.errors import InputCancelledError
from app.automation.input.failsafe import InputFailsafe
from app.automation.input.interruption_monitor import InterruptionMonitor
from app.automation.input.models import (
    InputSource,
    TypingProfile,
    get_typing_interval_seconds,
)
from app.automation.input.native_input import NativeInputBackend
from app.automation.input.pyautogui_fallback import PyAutoGUIInputBackend
from app.logging import logger
from app.tools.execution.cancellation import CancellationToken


class KeyboardController:
    """Controls keyboard key presses, hotkey combinations, and human-like typing profiles."""

    def __init__(
        self,
        native_backend: NativeInputBackend | None = None,
        pyautogui_backend: PyAutoGUIInputBackend | None = None,
        failsafe: InputFailsafe | None = None,
        interruption_monitor: InterruptionMonitor | None = None,
    ) -> None:
        self.native_backend = native_backend or NativeInputBackend()
        self.pyautogui_backend = pyautogui_backend or PyAutoGUIInputBackend()
        self.failsafe = failsafe or InputFailsafe()
        self.interruption_monitor = interruption_monitor or InterruptionMonitor()

    def press_key(
        self,
        key_name: str,
        backend: InputSource = InputSource.NATIVE,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Press single keyboard key."""
        if cancellation_token and cancellation_token.is_cancelled:
            raise InputCancelledError(f"Press key '{key_name}' cancelled.")

        if dry_run:
            logger.debug(f"[DRY-RUN] Keyboard press_key: '{key_name}'")
            return

        self.failsafe.check_failsafe()
        self.interruption_monitor.check_interruption()

        if backend == InputSource.PYAUTOGUI and self.pyautogui_backend.is_available():
            self.pyautogui_backend.press_key(key_name)
        else:
            self.native_backend.press_key(key_name)

    def key_down(
        self,
        key_name: str,
        backend: InputSource = InputSource.NATIVE,
        dry_run: bool = False,
    ) -> None:
        """Send key down event."""
        if dry_run:
            logger.debug(f"[DRY-RUN] Keyboard key_down: '{key_name}'")
            return

        self.failsafe.check_failsafe()
        self.interruption_monitor.check_interruption()

        if backend == InputSource.PYAUTOGUI and self.pyautogui_backend.is_available():
            self.pyautogui_backend.key_down(key_name)
        else:
            self.native_backend.key_down(key_name)

    def key_up(
        self,
        key_name: str,
        backend: InputSource = InputSource.NATIVE,
        dry_run: bool = False,
    ) -> None:
        """Send key up event."""
        if dry_run:
            logger.debug(f"[DRY-RUN] Keyboard key_up: '{key_name}'")
            return

        if backend == InputSource.PYAUTOGUI and self.pyautogui_backend.is_available():
            self.pyautogui_backend.key_up(key_name)
        else:
            self.native_backend.key_up(key_name)

    def press_hotkey(
        self,
        keys: list[str],
        backend: InputSource = InputSource.NATIVE,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Press key combination (hotkey) with automatic modifier cleanup."""
        if not keys:
            return

        if cancellation_token and cancellation_token.is_cancelled:
            raise InputCancelledError("Hotkey combination cancelled before execution.")

        if dry_run:
            logger.debug(f"[DRY-RUN] Keyboard press_hotkey: {keys}")
            return

        self.failsafe.check_failsafe()
        self.interruption_monitor.check_interruption()

        try:
            if (
                backend == InputSource.PYAUTOGUI
                and self.pyautogui_backend.is_available()
            ):
                self.pyautogui_backend.press_hotkey(keys)
            else:
                self.native_backend.press_hotkey(keys)
        finally:
            # Ensure modifiers are released even on error
            if not dry_run:
                self.native_backend.release_all_inputs()

    def type_text(
        self,
        text: str,
        profile: TypingProfile | str = TypingProfile.NORMAL,
        interval_ms: float | None = None,
        backend: InputSource = InputSource.NATIVE,
        dry_run: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> None:
        """Execute text typing with human-like timing profile and cancellation checks per character."""
        if not text:
            return

        if interval_ms is not None and interval_ms >= 0:
            delay_sec = interval_ms / 1000.0
        else:
            delay_sec = get_typing_interval_seconds(profile)

        if dry_run:
            logger.debug(
                f"[DRY-RUN] Keyboard type_text: len={len(text)} chars | profile={profile} | delay={delay_sec}s"
            )
            return

        self.failsafe.check_failsafe()
        self.interruption_monitor.check_interruption()

        try:
            for char in text:
                if cancellation_token and cancellation_token.is_cancelled:
                    raise InputCancelledError(
                        f"Typing operation cancelled: {cancellation_token.reason}"
                    )

                self.failsafe.check_failsafe()
                self.interruption_monitor.check_interruption()

                if (
                    backend == InputSource.PYAUTOGUI
                    and self.pyautogui_backend.is_available()
                ):
                    self.pyautogui_backend.type_text(char, interval_sec=0.0)
                else:
                    self.native_backend.type_text_unicode(char, interval_sec=0.0)

                if delay_sec > 0:
                    time.sleep(delay_sec)
        finally:
            self.native_backend.release_all_inputs()
