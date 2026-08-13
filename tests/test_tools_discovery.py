"""Unit tests for ToolDiscoveryService filtering and search."""

from app.tools.builtin.application_info_tool import ApplicationInfoTool
from app.tools.builtin.echo_tool import EchoTool
from app.tools.categories import ToolCategory
from app.tools.discovery.tool_discovery import ToolDiscoveryService
from app.tools.registry.tool_registry import ToolRegistry


def test_tool_discovery_filters():
    registry = ToolRegistry()
    registry.clear()

    echo = EchoTool()
    app_info = ApplicationInfoTool()

    registry.register_tool(echo)
    registry.register_tool(app_info)

    discovery = ToolDiscoveryService(registry=registry)

    # Category filter
    sys_tools = discovery.find_by_category(ToolCategory.SYSTEM)
    assert len(sys_tools) == 2

    # Tag filter
    echo_tags = discovery.find_by_tag("echo")
    assert len(echo_tags) == 1
    assert echo_tags[0].tool_id == "system.echo"

    # Search query
    search_res = discovery.search_tools("application metadata")
    assert len(search_res) >= 1
    assert search_res[0].tool_id == "system.get_application_info"
