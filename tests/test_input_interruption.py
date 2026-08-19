"""Unit tests for InterruptionMonitor physical user override detection and state management."""

from unittest.mock import MagicMock

import pytest

from app.automation.input.errors import InputInterruptedError
from app.automation.input.interruption_monitor import InterruptionMonitor


def test_interruption_monitor_lifecycle() -> None:
    """Verify monitoring start, position registration, and stop."""
    monitor = InterruptionMonitor(enabled=True)
    monitor.start_monitoring()
    assert monitor._automation_active is True

    monitor.update_expected_position(500, 500)
    assert monitor._expected_cursor_pos == (500, 500)

    monitor.stop_monitoring()
    assert monitor._automation_active is False


def test_interruption_trigger_invokes_release_callback() -> None:
    """Verify physical user interruption triggers emergency release callback."""
    mock_release = MagicMock()
    monitor = InterruptionMonitor(enabled=True, release_callback=mock_release)

    with pytest.raises(InputInterruptedError, match="MOUSE_INTERRUPT"):
        monitor._trigger_interruption("MOUSE_INTERRUPT")

    mock_release.assert_called_once()
