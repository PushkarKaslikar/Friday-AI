"""Unit tests for ToolRegistry registration and lookup."""

from app.tools.builtin.echo_tool import EchoTool
from app.tools.registry.tool_registry import ToolRegistry


def test_tool_registry_operations():
    registry = ToolRegistry()
    registry.clear()

    echo = EchoTool()
    assert registry.register_tool(echo) is True
    assert registry.registered_count == 1
    assert registry.has_tool("system.echo") is True
    assert registry.get_tool("system.echo") == echo

    # Disable tool
    assert registry.disable_tool("system.echo") is True
    tool = registry.get_tool("system.echo")
    assert tool is not None
    assert tool.metadata.is_enabled is False

    # Enable tool
    assert registry.enable_tool("system.echo") is True
    assert tool.metadata.is_enabled is True

    # Unregister tool
    assert registry.unregister_tool("system.echo") is True
    assert registry.has_tool("system.echo") is False
    assert registry.registered_count == 0
