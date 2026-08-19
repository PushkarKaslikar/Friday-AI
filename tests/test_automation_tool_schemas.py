"""Unit tests for Phase 6.6 Automation Tool Pydantic JSON schema generation."""

from app.ai.tool_calling.schema_registry import ToolSchemaRegistry
from app.tools.builtin.automation.application_tools import ApplicationLaunchTool
from app.tools.builtin.automation.clipboard_tools import ClipboardGetContentTool
from app.tools.builtin.automation.input_tools import InputMouseClickTool
from app.tools.builtin.automation.uia_tools import UiaFindElementTool
from app.tools.builtin.automation.window_tools import WindowFocusTool
from app.tools.builtin.automation.workflow_tools import WorkflowExecuteSequenceTool
from app.tools.registry.tool_registry import ToolRegistry


def test_automation_tool_schemas_generation():
    registry = ToolRegistry()
    registry.clear()
    registry.register_tool(UiaFindElementTool())
    registry.register_tool(InputMouseClickTool())
    registry.register_tool(WindowFocusTool())
    registry.register_tool(ClipboardGetContentTool())
    registry.register_tool(ApplicationLaunchTool())
    registry.register_tool(WorkflowExecuteSequenceTool())

    schema_reg = ToolSchemaRegistry(tool_registry=registry)
    definitions = schema_reg.generate_all_definitions()

    assert len(definitions) == 6
    tool_names = [d.tool_name for d in definitions]
    assert "uia.find_element" in tool_names
    assert "input.mouse_click" in tool_names
    assert "window.focus" in tool_names
    assert "workflow.execute_sequence" in tool_names
