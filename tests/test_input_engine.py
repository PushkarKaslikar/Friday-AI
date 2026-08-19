"""Unit and integration tests for InputEngine service contracts and channel exclusivity."""

from app.automation.input.input_engine import InputEngine
from app.automation.input.models import (
    InputStatus,
    InputTarget,
    TargetType,
    TypingProfile,
)


def test_input_engine_move_to_dry_run() -> None:
    """Verify InputEngine move_to dry-run execution."""
    engine = InputEngine(dry_run_mode=True)
    target = InputTarget(target_type=TargetType.SCREEN_COORDINATE, x=300, y=400)
    res = engine.move_to(target, duration=0.1)

    assert res.status == InputStatus.COMPLETED
    assert res.operation_type == "move_to"
    assert res.cancelled is False
    assert res.interrupted is False


def test_input_engine_click_dry_run() -> None:
    """Verify InputEngine click dry-run execution."""
    engine = InputEngine(dry_run_mode=True)
    target = InputTarget(target_type=TargetType.SCREEN_COORDINATE, x=200, y=200)
    res = engine.click(target)

    assert res.status == InputStatus.COMPLETED
    assert res.operation_type == "click"


def test_input_engine_typing_dry_run() -> None:
    """Verify InputEngine typing dry-run execution."""
    engine = InputEngine(dry_run_mode=True)
    res = engine.type_text("Hello World", profile=TypingProfile.FAST)

    assert res.status == InputStatus.COMPLETED
    assert res.operation_type == "type_text"


def test_input_engine_channel_busy() -> None:
    """Verify InputEngine returns INPUT_ENGINE_BUSY when channel is locked."""
    engine = InputEngine(dry_run_mode=True)
    engine._input_channel_lock.acquire()

    try:
        target = InputTarget(target_type=TargetType.SCREEN_COORDINATE, x=100, y=100)
        res = engine.move_to(target)
        assert res.status == InputStatus.INPUT_ENGINE_BUSY
    finally:
        engine._input_channel_lock.release()


def test_input_engine_health_report() -> None:
    """Verify InputEngine diagnostics health report."""
    engine = InputEngine()
    report = engine.diagnostics.get_health_report()
    assert report["status"] in ("HEALTHY", "DEGRADED", "UNAVAILABLE")
    assert report["channel_state"] == "IDLE"
