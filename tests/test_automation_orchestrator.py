"""Unit tests for Phase 4 AIOrchestrator and ToolCallingEngine integration with Phase 6.6 Automation Tools."""

from app.ai.tool_calling.models import ToolCall
from app.ai.tool_calling.tool_calling_engine import ToolCallingEngine
from app.tools.builtin.automation.uia_tools import UiaListWindowsTool
from app.tools.registry.tool_registry import ToolRegistry


def test_tool_calling_engine_executes_automation_tool():
    registry = ToolRegistry()
    registry.register_tool(UiaListWindowsTool())

    engine = ToolCallingEngine(tool_registry=registry)
    call = ToolCall(
        call_id="call_123", tool_name="uia.list_windows", arguments={"max_results": 5}
    )

    res = engine.execute_tool_call(call)

    assert res.status.value == "SUCCESS"
    assert res.result["status"] == "SUCCESS"
