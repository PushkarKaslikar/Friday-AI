"""Unit tests for Process tools and Protected Process Policy."""

import os

from app.tools.builtin.process_tools import (
    ProcessInfoTool,
    ProcessListTool,
    ProcessRunningTool,
    TerminateProcessTool,
)
from app.tools.models.errors import ToolErrorCode


def test_process_list_tool():
    tool = ProcessListTool()
    res = tool.execute({"limit": 10})
    assert res.success is True
    assert res.result_data["process_count"] >= 1


def test_process_info_tool():
    current_pid = os.getpid()
    tool = ProcessInfoTool()
    res = tool.execute({"pid": current_pid})
    assert res.success is True
    assert res.result_data["pid"] == current_pid


def test_process_running_tool():
    current_pid = os.getpid()
    tool = ProcessRunningTool()
    res = tool.execute({"process_identifier": str(current_pid)})
    assert res.success is True
    assert res.result_data["is_running"] is True


def test_protected_process_policy_termination():
    # Attempting to terminate PID 0 or system process must be rejected
    tool = TerminateProcessTool()

    # System process PID 4 or csrss
    res = tool.execute({"pid": 4})
    assert res.success is False
    assert res.error_code in (
        ToolErrorCode.PERMISSION_DENIED,
        ToolErrorCode.INVALID_INPUT,
    )
