"""Unit tests for WindowController, geometry manipulation, snapping, and normal window close."""

from unittest.mock import MagicMock, patch

import pytest

from app.automation.desktop.models import SnapPosition
from app.automation.desktop.monitor_manager import MonitorInfo, MonitorManager
from app.automation.desktop.window_controller import WindowController
from app.automation.uia.window_resolver import WindowCandidate


@pytest.fixture
def mock_monitor_manager():
    mgr = MagicMock(spec=MonitorManager)
    mgr.get_monitor_for_window.return_value = MonitorInfo(
        monitor_id=0,
        is_primary=True,
        x=0,
        y=0,
        width=1920,
        height=1080,
        work_left=0,
        work_top=0,
        work_right=1920,
        work_bottom=1040,
    )
    mgr.list_monitors.return_value = [mgr.get_monitor_for_window.return_value]
    return mgr


@pytest.fixture
def mock_window_resolver():
    res = MagicMock()
    res.enumerate_windows.return_value = [
        WindowCandidate(
            hwnd=1001,
            title="Notepad - Document.txt",
            process_id=1234,
            process_name="notepad.exe",
            class_name="Notepad",
            is_visible=True,
            is_enabled=True,
        ),
        WindowCandidate(
            hwnd=1002,
            title="Google Chrome",
            process_id=5678,
            process_name="chrome.exe",
            class_name="Chrome_WidgetWin_1",
            is_visible=True,
            is_enabled=True,
        ),
    ]
    res.get_window_by_handle.side_effect = lambda h: WindowCandidate(
        hwnd=h,
        title="Test",
        process_id=1234,
        process_name="test.exe",
        class_name="TestClass",
        is_visible=True,
        is_enabled=True,
    )
    return res


def test_list_windows_returns_desktop_windows(
    mock_window_resolver, mock_monitor_manager
):
    with patch("win32gui.IsWindow", return_value=True), patch(
        "win32gui.GetForegroundWindow", return_value=1001
    ), patch(
        "win32gui.GetWindowText",
        side_effect=lambda h: "Notepad" if h == 1001 else "Chrome",
    ), patch(
        "win32gui.GetClassName", return_value="TestClass"
    ), patch(
        "win32gui.IsWindowVisible", return_value=True
    ), patch(
        "win32gui.IsIconic", return_value=False
    ), patch(
        "win32gui.GetWindowPlacement",
        return_value=(0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600)),
    ), patch(
        "win32gui.GetWindowRect", return_value=(100, 100, 900, 700)
    ):

        ctrl = WindowController(
            window_resolver=mock_window_resolver, monitor_manager=mock_monitor_manager
        )
        windows = ctrl.list_windows()

        assert len(windows) == 2
        assert windows[0].hwnd == 1001
        assert windows[0].is_active is True
        assert windows[0].width == 800
        assert windows[0].height == 600


def test_get_active_window(mock_window_resolver, mock_monitor_manager):
    with patch("win32gui.GetForegroundWindow", return_value=1001), patch(
        "win32gui.IsWindow", return_value=True
    ), patch("win32gui.GetWindowText", return_value="Active Window"), patch(
        "win32gui.GetClassName", return_value="TestClass"
    ), patch(
        "win32gui.IsWindowVisible", return_value=True
    ), patch(
        "win32gui.IsIconic", return_value=False
    ), patch(
        "win32gui.GetWindowPlacement",
        return_value=(0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600)),
    ), patch(
        "win32gui.GetWindowRect", return_value=(0, 0, 500, 500)
    ):

        ctrl = WindowController(
            window_resolver=mock_window_resolver, monitor_manager=mock_monitor_manager
        )
        active = ctrl.get_active_window()

        assert active is not None
        assert active.hwnd == 1001
        assert active.is_active is True


def test_focus_window(mock_window_resolver, mock_monitor_manager):
    with patch("win32gui.IsWindow", return_value=True), patch(
        "win32gui.IsIconic", return_value=True
    ), patch("win32gui.ShowWindow") as mock_show, patch(
        "win32gui.SetForegroundWindow"
    ) as mock_set_fg, patch(
        "win32gui.GetForegroundWindow", return_value=1001
    ), patch(
        "win32gui.GetWindowText", return_value="Test Window"
    ), patch(
        "win32gui.GetClassName", return_value="TestClass"
    ), patch(
        "win32gui.IsWindowVisible", return_value=True
    ), patch(
        "win32gui.GetWindowPlacement",
        return_value=(0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600)),
    ), patch(
        "win32gui.GetWindowRect", return_value=(0, 0, 800, 600)
    ):

        ctrl = WindowController(
            window_resolver=mock_window_resolver, monitor_manager=mock_monitor_manager
        )
        res = ctrl.focus_window(1001)

        assert res.status == "COMPLETED"
        assert res.operation == "focus"
        mock_show.assert_called_once()
        mock_set_fg.assert_called_once_with(1001)


def test_snap_window_left(mock_window_resolver, mock_monitor_manager):
    with patch("win32gui.IsWindow", return_value=True), patch(
        "win32gui.IsIconic", return_value=False
    ), patch("win32gui.SetWindowPos") as mock_pos, patch(
        "win32gui.GetForegroundWindow", return_value=1001
    ), patch(
        "win32gui.GetWindowText", return_value="Test Window"
    ), patch(
        "win32gui.GetClassName", return_value="TestClass"
    ), patch(
        "win32gui.IsWindowVisible", return_value=True
    ), patch(
        "win32gui.GetWindowPlacement",
        return_value=(0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600)),
    ), patch(
        "win32gui.GetWindowRect", return_value=(0, 0, 960, 1040)
    ):

        ctrl = WindowController(
            window_resolver=mock_window_resolver, monitor_manager=mock_monitor_manager
        )
        res = ctrl.snap_window(1001, SnapPosition.LEFT)

        assert res.status == "COMPLETED"
        assert res.operation == "snap_left"
        mock_pos.assert_called_once_with(1001, 0, 0, 0, 960, 1040, 4)


def test_close_window_sends_wm_close(mock_window_resolver, mock_monitor_manager):
    with patch("win32gui.IsWindow", return_value=True), patch(
        "win32gui.PostMessage"
    ) as mock_post, patch("win32gui.GetForegroundWindow", return_value=1001), patch(
        "win32gui.GetWindowText", return_value="Test Window"
    ), patch(
        "win32gui.GetClassName", return_value="TestClass"
    ), patch(
        "win32gui.IsWindowVisible", return_value=True
    ), patch(
        "win32gui.IsIconic", return_value=False
    ), patch(
        "win32gui.GetWindowPlacement",
        return_value=(0, 1, (-1, -1), (-1, -1), (0, 0, 800, 600)),
    ), patch(
        "win32gui.GetWindowRect", return_value=(0, 0, 800, 600)
    ):

        ctrl = WindowController(
            window_resolver=mock_window_resolver, monitor_manager=mock_monitor_manager
        )
        res = ctrl.close_window(1001)

        assert res.status == "COMPLETED"
        assert res.operation == "close"
        mock_post.assert_called_once_with(1001, 16, 0, 0)
