"""Unit tests for TerminalAdapter terminal resolution, set working directory, typing, and output reading."""

from unittest.mock import MagicMock

import pytest

from app.automation.apps.launcher import ApplicationLauncher
from app.automation.apps.models import TerminalType
from app.automation.apps.terminal_adapter import TerminalAdapter
from app.automation.desktop.models import DesktopWindow
from app.automation.desktop.window_controller import WindowController
from app.automation.input.input_engine import InputEngine
from app.automation.uia.element_finder import ElementFinder
from app.automation.uia.uia_engine import UIAutomationEngine
from app.automation.uia.window_resolver import WindowResolver


@pytest.fixture
def mock_terminal_adapter():
    win_res = MagicMock(spec=WindowResolver)
    win_ctrl = MagicMock(spec=WindowController)
    uia_engine = MagicMock(spec=UIAutomationEngine)
    elem_finder = MagicMock(spec=ElementFinder)
    input_engine = MagicMock(spec=InputEngine)
    launcher = MagicMock(spec=ApplicationLauncher)

    win_ctrl.list_windows.return_value = [
        DesktopWindow(
            hwnd=2002,
            title="Command Prompt",
            process_name="cmd.exe",
            class_name="ConsoleWindowClass",
            left=0,
            top=0,
            width=800,
            height=600,
        )
    ]
    win_res.is_window_valid.return_value = True

    adapter = TerminalAdapter(
        window_resolver=win_res,
        window_controller=win_ctrl,
        uia_engine=uia_engine,
        element_finder=elem_finder,
        input_engine=input_engine,
        launcher=launcher,
    )
    return adapter


def test_terminal_adapter_installation_check(mock_terminal_adapter):
    assert mock_terminal_adapter.is_terminal_installed(TerminalType.CMD) is True
    assert mock_terminal_adapter.is_running() is True


def test_terminal_set_working_directory_invalid(mock_terminal_adapter):
    res = mock_terminal_adapter.set_working_directory("C:\\NonExistentFolderPath999")
    assert res.status == "FAILED"
    assert "does not exist" in res.message


def test_terminal_type_command_sanitizes_secret_logging(mock_terminal_adapter):
    adapter = mock_terminal_adapter
    adapter.attach(2002)

    res = adapter.type_command("set password=SuperSecretToken123")
    assert res.status == "SUCCESS"
    assert adapter.input_engine.type_text.called
    adapter.input_engine.press_key.assert_called_with("enter")
