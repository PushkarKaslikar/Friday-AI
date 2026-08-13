"""Unit tests for safe builtin tools execution and error handling."""

from app.tools.builtin.application_info_tool import ApplicationInfoTool
from app.tools.builtin.echo_tool import EchoTool
from app.tools.builtin.runtime_status_tool import RuntimeStatusTool
from app.tools.models.errors import ToolErrorCode


def test_echo_tool_execution():
    tool = EchoTool()
    tool.initialize()
    tool.start()

    res = tool.execute({"message": "Friday AI", "repeat": 2})
    assert res.success is True
    assert res.result_data["echoed_text"] == "Friday AI Friday AI"
    assert res.result_data["length"] == 19
    assert res.execution_duration >= 0.0

    tool.stop()


def test_echo_tool_invalid_input():
    tool = EchoTool()
    tool.initialize()
    tool.start()

    # repeat must be <= 10
    res = tool.execute({"message": "Test", "repeat": 100})
    assert res.success is False
    assert res.error_code == ToolErrorCode.INVALID_INPUT
    assert "Input validation failed" in res.error

    tool.stop()


def test_application_info_tool():
    tool = ApplicationInfoTool()
    tool.initialize()
    tool.start()

    res = tool.execute({"include_build_details": True})
    assert res.success is True
    assert res.result_data["name"] == "Friday AI Assistant"
    assert "version" in res.result_data

    tool.stop()


def test_runtime_status_tool():
    tool = RuntimeStatusTool()
    tool.initialize()
    tool.start()

    res = tool.execute({"include_services": True})
    assert res.success is True
    assert res.result_data["status"] == "RUNNING"

    tool.stop()
