"""Unit tests for ToolExecutor pipeline execution."""

from app.tools.builtin.application_info_tool import ApplicationInfoTool
from app.tools.builtin.echo_tool import EchoTool
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.models.command import Command, CommandSource
from app.tools.models.errors import ToolErrorCode
from app.tools.models.request import ToolRequest
from app.tools.registry.tool_registry import ToolRegistry
from app.tools.security.authorization_provider import DevAuthorizationProvider


def test_tool_executor_pipeline_success():
    registry = ToolRegistry()
    registry.clear()

    echo = EchoTool()
    registry.register_tool(echo)

    auth = DevAuthorizationProvider(mode="ALLOW_ALL")
    executor = ToolExecutor(registry=registry, auth_provider=auth)
    executor.initialize()
    executor.start()

    res = executor.execute("system.echo", {"message": "Hello Executor", "repeat": 2})
    assert res.success is True
    assert res.result_data["echoed_text"] == "Hello Executor Hello Executor"
    assert res.execution_duration >= 0.0

    executor.stop()


def test_tool_executor_command_execution():
    registry = ToolRegistry()
    registry.clear()

    app_info = ApplicationInfoTool()
    registry.register_tool(app_info)

    auth = DevAuthorizationProvider(mode="ALLOW_ALL")
    executor = ToolExecutor(registry=registry, auth_provider=auth)
    executor.initialize()
    executor.start()

    cmd = Command(
        tool_name="system.get_application_info",
        arguments={"include_build_details": True},
        source=CommandSource.USER,
    )

    res = executor.execute_command(cmd)
    assert res.success is True
    assert res.result_data["name"] == "Friday AI Assistant"

    executor.stop()


def test_tool_executor_request_execution():
    registry = ToolRegistry()
    registry.clear()

    echo = EchoTool()
    registry.register_tool(echo)

    auth = DevAuthorizationProvider(mode="ALLOW_ALL")
    executor = ToolExecutor(registry=registry, auth_provider=auth)
    executor.initialize()
    executor.start()

    req = ToolRequest(
        tool_id="system.echo",
        arguments={"message": "Request Test"},
    )

    res = executor.execute_request(req)
    assert res.success is True
    assert res.result_data["echoed_text"] == "Request Test"

    executor.stop()


def test_tool_executor_tool_not_found():
    registry = ToolRegistry()
    registry.clear()

    executor = ToolExecutor(registry=registry)
    res = executor.execute("nonexistent.tool", {})

    assert res.success is False
    assert res.error_code == ToolErrorCode.TOOL_NOT_FOUND


def test_tool_executor_tool_disabled():
    registry = ToolRegistry()
    registry.clear()

    echo = EchoTool()
    registry.register_tool(echo)
    registry.disable_tool("system.echo")

    executor = ToolExecutor(registry=registry)
    res = executor.execute("system.echo", {"message": "test"})

    assert res.success is False
    assert res.error_code == ToolErrorCode.TOOL_DISABLED


def test_tool_executor_invalid_input():
    registry = ToolRegistry()
    registry.clear()

    echo = EchoTool()
    registry.register_tool(echo)

    auth = DevAuthorizationProvider(mode="ALLOW_ALL")
    executor = ToolExecutor(registry=registry, auth_provider=auth)
    executor.initialize()
    executor.start()

    # repeat must be <= 10
    res = executor.execute("system.echo", {"message": "test", "repeat": 999})

    assert res.success is False
    assert res.error_code == ToolErrorCode.INVALID_INPUT

    executor.stop()


def test_tool_executor_authorization_denied():
    registry = ToolRegistry()
    registry.clear()

    echo = EchoTool()
    registry.register_tool(echo)

    auth = DevAuthorizationProvider(mode="DENY_ALL")
    executor = ToolExecutor(registry=registry, auth_provider=auth)

    res = executor.execute("system.echo", {"message": "test"})
    assert res.success is False
    assert res.error_code == ToolErrorCode.PERMISSION_DENIED
