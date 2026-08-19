"""Unit tests for KeyboardController, hotkeys, typing profiles, and dry-run execution."""

import pytest

from app.automation.input.errors import InputCancelledError
from app.automation.input.keyboard_controller import KeyboardController
from app.automation.input.models import TypingProfile
from app.tools.execution.cancellation import CancellationToken


def test_keyboard_press_dry_run() -> None:
    """Verify dry-run key press executes cleanly."""
    ctrl = KeyboardController()
    ctrl.press_key("enter", dry_run=True)
    ctrl.key_down("ctrl", dry_run=True)
    ctrl.key_up("ctrl", dry_run=True)


def test_keyboard_hotkey_dry_run() -> None:
    """Verify dry-run hotkey executes cleanly."""
    ctrl = KeyboardController()
    ctrl.press_hotkey(["ctrl", "shift", "esc"], dry_run=True)


def test_keyboard_typing_dry_run() -> None:
    """Verify dry-run text typing with profiles."""
    ctrl = KeyboardController()
    ctrl.type_text("Test typing string", profile=TypingProfile.FAST, dry_run=True)


def test_keyboard_typing_cancellation() -> None:
    """Verify cooperative cancellation during typing."""
    ctrl = KeyboardController()
    token = CancellationToken()
    token.request_cancellation("Unit test cancel")
    with pytest.raises(InputCancelledError, match="cancelled"):
        ctrl.type_text("Hello World", cancellation_token=token)
