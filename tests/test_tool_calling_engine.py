"""Comprehensive test suite for Tool Calling & Function Binding Engine.

Phase 4.3 - Tool Calling & Function Binding Engine
"""

from pydantic import BaseModel, Field

from app.ai.tool_calling.models import (
    ToolCall,
    ToolCallingConfiguration,
    ToolCallStatus,
)
from app.ai.tool_calling.provider_adapter import DefaultToolCallAdapter
from app.ai.tool_calling.schema_registry import ToolSchemaRegistry
from app.ai.tool_calling.tool_calling_engine import ToolCallingEngine
from app.bootstrap.bootstrapper import AppBootstrapper
from app.services.events.event_bus import EventBus
from app.tools.base.metadata import ToolCategory, ToolMetadata
from app.tools.base.tool import BaseTool
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.models.result import ToolResult
from app.tools.registry.tool_registry import ToolRegistry


class SampleInputSchema(BaseModel):
    """Pydantic input schema for tool calling tests."""

    target_app: str = Field(description="Name of the application to launch")
    count: int = Field(default=1, description="Number of instances")


class SampleSystemTool(BaseTool):
    """Sample tool for testing tool calling engine validation and execution."""

    def __init__(self) -> None:
        metadata = ToolMetadata(
            tool_id="system.launch_app",
            name="system.launch_app",
            display_name="Launch Application",
            description="Launches a specified system application.",
            category=ToolCategory.SYSTEM,
            input_schema=SampleInputSchema,
        )
        super().__init__(metadata)

    def _execute(self, arguments: dict) -> ToolResult:
        app_name = arguments.get("target_app", "unknown")
        return ToolResult.success_result(
            result_id="res-launch-1",
            result={"status": "launched", "app": app_name, "api_key": "SECRET_KEY_123"},
        )


def test_tool_calling_config_defaults():
    """Verify default ToolCallingConfiguration settings."""
    cfg = ToolCallingConfiguration()
    assert cfg.enabled is True
    assert cfg.max_tool_definitions == 20
    assert cfg.max_result_chars == 4000
    assert cfg.duplicate_call_protection is True
    assert cfg.schema_cache_enabled is True


def test_schema_registry_generation_and_caching():
    """Verify ToolSchemaRegistry generates canonical JSON schemas and caches them."""
    registry = ToolRegistry()
    registry.clear()
    tool = SampleSystemTool()
    registry.register_tool(tool)

    schema_reg = ToolSchemaRegistry(tool_registry=registry)
    defn = schema_reg.get_tool_definition("system.launch_app")

    assert defn is not None
    assert defn.tool_name == "system.launch_app"
    assert "target_app" in defn.parameters_schema
    assert defn.required_parameters == ["target_app"]

    # Verify cache hit
    defn_cached = schema_reg.get_tool_definition("system.launch_app")
    assert defn_cached is defn


def test_provider_adapter_parsing():
    """Verify DefaultToolCallAdapter parses string JSON, dict, and OpenAI wire formats."""
    adapter = DefaultToolCallAdapter()

    # Format 1: Friday JSON string
    json_str = (
        '{"tool_call": {"name": "system.echo", "arguments": {"message": "hello"}}}'
    )
    call1 = adapter.parse(json_str)
    assert call1 is not None
    assert call1.tool_name == "system.echo"
    assert call1.arguments == {"message": "hello"}

    # Format 2: OpenAI style function dict
    openai_dict = {
        "function": {
            "name": "browser.open",
            "arguments": '{"url": "https://google.com"}',
        }
    }
    call2 = adapter.parse(openai_dict)
    assert call2 is not None
    assert call2.tool_name == "browser.open"
    assert call2.arguments == {"url": "https://google.com"}


def test_validate_tool_call_unknown_and_disabled_tools():
    """Verify validation rejects unknown and disabled tools."""
    registry = ToolRegistry()
    registry.clear()
    tool = SampleSystemTool()
    registry.register_tool(tool)

    engine = ToolCallingEngine(tool_registry=registry)

    # 1. Unknown tool
    bad_call = ToolCall(call_id="c1", tool_name="system.non_existent", arguments={})
    is_valid, status, _err = engine.validate_tool_call(bad_call)
    assert is_valid is False
    assert status == ToolCallStatus.UNKNOWN_TOOL

    # 2. Disabled tool
    registry.disable_tool("system.launch_app")
    disabled_call = ToolCall(
        call_id="c2", tool_name="system.launch_app", arguments={"target_app": "notepad"}
    )
    is_valid, status, _err = engine.validate_tool_call(disabled_call)
    assert is_valid is False
    assert status == ToolCallStatus.REJECTED


def test_validate_tool_call_invalid_arguments():
    """Verify validation rejects missing required arguments or type mismatches."""
    registry = ToolRegistry()
    registry.clear()
    tool = SampleSystemTool()
    registry.register_tool(tool)

    engine = ToolCallingEngine(tool_registry=registry)

    # Missing required argument 'target_app'
    missing_arg_call = ToolCall(
        call_id="c3", tool_name="system.launch_app", arguments={}
    )
    is_valid, status, err = engine.validate_tool_call(missing_arg_call)
    assert is_valid is False
    assert status == ToolCallStatus.INVALID_ARGUMENTS
    assert "target_app" in str(err)


def test_execute_tool_call_delegation_and_sanitization():
    """Verify tool execution delegates to ToolExecutor, masks secrets, and builds model output tags."""
    event_bus = EventBus()
    registry = ToolRegistry(event_bus=event_bus)
    registry.clear()
    tool = SampleSystemTool()
    registry.register_tool(tool)

    executor = ToolExecutor(registry=registry, event_bus=event_bus)
    executor.initialize()
    executor.start()

    engine = ToolCallingEngine(
        event_bus=event_bus, tool_registry=registry, tool_executor=executor
    )
    engine.initialize()
    engine.start()

    call = ToolCall(
        call_id="c4",
        tool_name="system.launch_app",
        arguments={"target_app": "chrome"},
    )
    result = engine.execute_tool_call(call)

    assert result.status == ToolCallStatus.SUCCESS
    assert result.result["app"] == "chrome"
    # Sensitive credential 'api_key' masked in sanitized_result
    assert result.sanitized_result["api_key"] == "********"

    # Verify model-facing prompt injection isolation output format
    assert (
        '<TOOL_RESULT call_id="c4" tool_name="system.launch_app" status="SUCCESS">'
        in result.model_facing_output
    )
    assert "********" in result.model_facing_output

    executor.stop()
    engine.stop()


def test_bootstrapper_integration_and_health_check(qapp):
    """Verify ToolCallingEngine integration into AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        engine: ToolCallingEngine = result.container.tool_calling_engine()
        assert engine is not None
        report = engine.get_health_report()

        assert report["subsystem"] == "Tool Calling & Function Binding Engine"
        assert report["status"] == "HEALTHY"
        assert report["registered_tools_count"] > 0
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()


def test_security_boundary_no_eval_exec():
    """Verify tool calling engine contains zero dynamic eval/exec code evaluation."""
    engine = ToolCallingEngine()
    import inspect

    source = inspect.getsource(engine.__class__)
    assert "eval(" not in source
    assert "exec(" not in source
