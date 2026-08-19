"""Unit tests for ApplicationLauncher executable resolution, working directory validation, and launch requests."""

import os
from unittest.mock import MagicMock

import pytest

from app.automation.apps.errors import (
    InvalidExecutableError,
    InvalidWorkingDirectoryError,
)
from app.automation.apps.launcher import ApplicationLauncher
from app.automation.apps.models import LaunchRequest
from app.automation.desktop.window_controller import WindowController
from app.automation.uia.window_resolver import WindowResolver


@pytest.fixture
def mock_window_resolver():
    res = MagicMock(spec=WindowResolver)
    res.enumerate_windows.return_value = []
    return res


@pytest.fixture
def mock_window_controller():
    ctrl = MagicMock(spec=WindowController)
    return ctrl


def test_resolve_executable_alias(mock_window_resolver, mock_window_controller):
    launcher = ApplicationLauncher(mock_window_resolver, mock_window_controller)
    cmd_path = launcher.resolve_executable("cmd")
    assert "cmd" in cmd_path.lower()


def test_resolve_executable_invalid_extension(
    mock_window_resolver, mock_window_controller
):
    launcher = ApplicationLauncher(mock_window_resolver, mock_window_controller)
    with pytest.raises(InvalidExecutableError, match="Disallowed executable extension"):
        launcher.resolve_executable("script.py", explicit_path=__file__)


def test_validate_working_directory_valid(mock_window_resolver, mock_window_controller):
    launcher = ApplicationLauncher(mock_window_resolver, mock_window_controller)
    cwd = launcher.validate_working_directory(os.getcwd())
    assert cwd == os.getcwd()


def test_validate_working_directory_invalid(
    mock_window_resolver, mock_window_controller
):
    launcher = ApplicationLauncher(mock_window_resolver, mock_window_controller)
    with pytest.raises(InvalidWorkingDirectoryError, match="does not exist"):
        launcher.validate_working_directory("C:\\NonExistentFolderPath999")


def test_launch_invalid_executable_returns_result(
    mock_window_resolver, mock_window_controller
):
    launcher = ApplicationLauncher(mock_window_resolver, mock_window_controller)
    req = LaunchRequest(application="non_existent_app_xyz")
    res = launcher.launch(req)
    assert res.status == "INVALID_EXECUTABLE"
    assert res.state.value == "FAILED"
