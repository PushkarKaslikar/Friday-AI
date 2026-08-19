"""Unit tests for MouseController, movement easing, clicks, drag-and-drop, and dry-run mode."""

from app.automation.input.models import (
    EasingProfile,
    InputTarget,
    MouseButton,
    TargetType,
)
from app.automation.input.mouse_controller import MouseController


def test_mouse_easing_calculations() -> None:
    """Verify normalization of easing profiles."""
    ctrl = MouseController()
    assert ctrl._apply_easing(0.0, EasingProfile.LINEAR) == 0.0
    assert ctrl._apply_easing(1.0, EasingProfile.LINEAR) == 1.0
    assert ctrl._apply_easing(0.5, EasingProfile.LINEAR) == 0.5

    assert 0.0 <= ctrl._apply_easing(0.5, EasingProfile.EASE_IN_OUT) <= 1.0
    assert 0.0 <= ctrl._apply_easing(0.5, EasingProfile.SMOOTH) <= 1.0


def test_mouse_move_dry_run() -> None:
    """Verify dry-run mouse move returns valid target without hardware calls."""
    ctrl = MouseController()
    target = InputTarget(target_type=TargetType.SCREEN_COORDINATE, x=250, y=350)
    pos = ctrl.move_to(target, duration=0.0, dry_run=True)
    assert pos.x == 250
    assert pos.y == 350


def test_mouse_click_dry_run() -> None:
    """Verify dry-run click returns position without hardware interaction."""
    ctrl = MouseController()
    target = InputTarget(target_type=TargetType.SCREEN_COORDINATE, x=100, y=100)
    pos = ctrl.click(target, button=MouseButton.RIGHT, click_count=2, dry_run=True)
    assert pos.x == 100
    assert pos.y == 100


def test_mouse_drag_and_drop_dry_run() -> None:
    """Verify dry-run drag and drop returns start and end positions."""
    ctrl = MouseController()
    start = InputTarget(target_type=TargetType.SCREEN_COORDINATE, x=100, y=100)
    end = InputTarget(target_type=TargetType.SCREEN_COORDINATE, x=400, y=400)
    sp, ep = ctrl.drag_and_drop(start, end, duration=0.1, dry_run=True)
    assert sp.x == 100 and sp.y == 100
    assert ep.x == 400 and ep.y == 400
