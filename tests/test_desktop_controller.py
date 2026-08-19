"""Unit tests for DesktopController coordinator service and DesktopSnapshot generation."""

from unittest.mock import MagicMock

import pytest

from app.automation.desktop.desktop_controller import DesktopController
from app.automation.desktop.models import (
    ClipboardFormat,
    DesktopSnapshot,
    DesktopWindow,
    MonitorInfo,
    VirtualDesktopInfo,
)


@pytest.fixture
def mock_desktop_controller():
    win_ctrl = MagicMock()
    win_ctrl.get_active_window.return_value = DesktopWindow(
        hwnd=1001,
        title="Active Notepad",
        process_name="notepad.exe",
        left=0,
        top=0,
        width=800,
        height=600,
        is_active=True,
    )
    win_ctrl.list_windows.return_value = [win_ctrl.get_active_window.return_value]

    mon_mgr = MagicMock()
    mon_mgr.list_monitors.return_value = [
        MonitorInfo(monitor_id=0, is_primary=True, x=0, y=0, width=1920, height=1080)
    ]

    vdesktop_mgr = MagicMock()
    vdesktop_mgr.get_virtual_desktop_info.return_value = VirtualDesktopInfo(
        is_available=True, current_desktop_id="d1", total_desktops=1
    )

    cb_mgr = MagicMock()
    cb_mgr.inspect_format.return_value = ClipboardFormat.TEXT

    return DesktopController(
        window_controller=win_ctrl,
        monitor_manager=mon_mgr,
        virtual_desktop_manager=vdesktop_mgr,
        clipboard_manager=cb_mgr,
    )


def test_get_desktop_snapshot(mock_desktop_controller):
    snapshot = mock_desktop_controller.get_desktop_snapshot()

    assert isinstance(snapshot, DesktopSnapshot)
    assert snapshot.active_window is not None
    assert snapshot.active_window.hwnd == 1001
    assert len(snapshot.windows) == 1
    assert len(snapshot.monitors) == 1
    assert mock_desktop_controller.metrics.total_operations >= 1
