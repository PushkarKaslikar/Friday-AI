"""Unit tests for Power Management tools (Safety Stubbed)."""

from app.tools.builtin.power_tools import (
    LockComputerTool,
    RestartComputerTool,
    ShutdownComputerTool,
    SleepComputerTool,
)


def test_lock_computer_tool():
    tool = LockComputerTool()
    res = tool.execute({})
    assert res.success is True
    assert res.result_data["locked"] is True


def test_sleep_computer_tool():
    tool = SleepComputerTool()
    res = tool.execute({})
    assert res.success is True
    assert res.result_data["sleep_initiated"] is True


def test_restart_computer_tool():
    tool = RestartComputerTool()
    res = tool.execute({"force": False})
    assert res.success is True
    assert res.result_data["restart_initiated"] is True


def test_shutdown_computer_tool():
    tool = ShutdownComputerTool()
    res = tool.execute({"force": False})
    assert res.success is True
    assert res.result_data["shutdown_initiated"] is True
