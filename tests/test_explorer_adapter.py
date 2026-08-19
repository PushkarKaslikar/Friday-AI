"""Unit tests for ExplorerAdapter navigation, current location query, and directory creation."""

from unittest.mock import MagicMock

import pytest

from app.automation.apps.explorer_adapter import ExplorerAdapter
from app.automation.apps.launcher import ApplicationLauncher
from app.automation.desktop.models import DesktopWindow
from app.automation.desktop.window_controller import WindowController
from app.automation.input.input_engine import InputEngine
from app.automation.uia.element_finder import ElementFinder
from app.automation.uia.uia_engine import UIAutomationEngine
from app.automation.uia.window_resolver import WindowResolver
from app.platform.filesystem.filesystem_service import FilesystemService


@pytest.fixture
def mock_explorer_adapter():
    win_res = MagicMock(spec=WindowResolver)
    win_ctrl = MagicMock(spec=WindowController)
    uia_engine = MagicMock(spec=UIAutomationEngine)
    elem_finder = MagicMock(spec=ElementFinder)
    input_engine = MagicMock(spec=InputEngine)
    fs_service = MagicMock(spec=FilesystemService)
    launcher = MagicMock(spec=ApplicationLauncher)

    win_ctrl.list_windows.return_value = [
        DesktopWindow(
            hwnd=1001,
            title="Documents",
            process_name="explorer.exe",
            class_name="CabinetWClass",
            left=0,
            top=0,
            width=800,
            height=600,
        )
    ]
    win_res.is_window_valid.return_value = True

    adapter = ExplorerAdapter(
        window_resolver=win_res,
        window_controller=win_ctrl,
        uia_engine=uia_engine,
        element_finder=elem_finder,
        input_engine=input_engine,
        filesystem_service=fs_service,
        launcher=launcher,
    )
    return adapter


def test_explorer_adapter_identity_and_installation(mock_explorer_adapter):
    assert mock_explorer_adapter.identity.app_id == "explorer"
    assert mock_explorer_adapter.is_installed() is True
    assert mock_explorer_adapter.is_running() is True


def test_explorer_navigate_invalid_path(mock_explorer_adapter):
    res = mock_explorer_adapter.navigate_to("C:\\NonExistentFolderPath999")
    assert res.status == "NAVIGATION_FAILED"
    assert "does not exist" in res.message


def test_explorer_create_folder(mock_explorer_adapter):
    mock_explorer_adapter.filesystem_service.create_folder.return_value = {
        "path": "D:\\Friday AI\\test_dir",
        "created": True,
    }
    res = mock_explorer_adapter.create_folder("D:\\Friday AI\\test_dir")
    assert res.status == "SUCCESS"
    assert res.current_path == "D:\\Friday AI\\test_dir"
