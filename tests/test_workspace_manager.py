"""Unit tests for WorkspaceManager desktop layout capture and restoration."""

from unittest.mock import MagicMock

import pytest

from app.automation.desktop.models import DesktopWindow, WorkspaceLayout
from app.automation.desktop.workspace_manager import WorkspaceManager


@pytest.fixture
def mock_window_controller():
    ctrl = MagicMock()
    ctrl.list_windows.return_value = [
        DesktopWindow(
            hwnd=1001,
            title="Editor",
            process_name="code.exe",
            class_name="Code",
            left=0,
            top=0,
            width=800,
            height=600,
        ),
        DesktopWindow(
            hwnd=1002,
            title="Browser",
            process_name="chrome.exe",
            class_name="Chrome",
            left=800,
            top=0,
            width=800,
            height=600,
        ),
    ]
    return ctrl


@pytest.fixture
def mock_monitor_manager():
    mgr = MagicMock()
    mgr.list_monitors.return_value = []
    return mgr


def test_capture_workspace_layout(mock_window_controller, mock_monitor_manager):
    mgr = WorkspaceManager(
        window_controller=mock_window_controller, monitor_manager=mock_monitor_manager
    )
    layout = mgr.capture_workspace_layout()

    assert isinstance(layout, WorkspaceLayout)
    assert len(layout.windows) == 2
    assert layout.windows[0].title == "Editor"
    assert layout.windows[1].title == "Browser"


def test_restore_workspace_layout_partial_skips_missing(
    mock_window_controller, mock_monitor_manager
):
    mgr = WorkspaceManager(
        window_controller=mock_window_controller, monitor_manager=mock_monitor_manager
    )
    layout = mgr.capture_workspace_layout()

    # Change active windows so only Editor remains
    mock_window_controller.list_windows.return_value = [
        DesktopWindow(
            hwnd=1001,
            title="Editor",
            process_name="code.exe",
            class_name="Code",
            left=0,
            top=0,
            width=800,
            height=600,
        )
    ]

    res = mgr.restore_workspace_layout(layout)

    assert res["status"] == "COMPLETED"
    assert res["restored"] == 1
    assert res["skipped"] == 1
    assert res["failed"] == 0
