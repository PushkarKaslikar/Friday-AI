"""Unit tests for Phase 6.6 Automation Tool Suite registration and execution."""

from unittest.mock import MagicMock

from app.tools.builtin.automation.application_tools import (
    ApplicationLaunchTool,
)
from app.tools.builtin.automation.clipboard_tools import (
    ClipboardGetContentTool,
)
from app.tools.builtin.automation.explorer_tools import (
    ExplorerNavigateTool,
)
from app.tools.builtin.automation.input_tools import (
    InputMouseClickTool,
)
from app.tools.builtin.automation.screen_tools import (
    ScreenCaptureTool,
)
from app.tools.builtin.automation.terminal_tools import (
    TerminalLaunchTool,
)
from app.tools.builtin.automation.uia_tools import (
    UiaListWindowsTool,
)
from app.tools.builtin.automation.window_tools import (
    WindowFocusTool,
)
from app.tools.builtin.automation.workflow_tools import WorkflowExecuteSequenceTool


def test_automation_tools_instantiation():
    uia_tool = UiaListWindowsTool()
    assert uia_tool.tool_id == "uia.list_windows"

    input_tool = InputMouseClickTool()
    assert input_tool.tool_id == "input.mouse_click"

    window_tool = WindowFocusTool()
    assert window_tool.tool_id == "window.focus"

    screen_tool = ScreenCaptureTool()
    assert screen_tool.tool_id == "screen.capture"

    clipboard_tool = ClipboardGetContentTool()
    assert clipboard_tool.tool_id == "clipboard.get_content"

    app_tool = ApplicationLaunchTool()
    assert app_tool.tool_id == "application.launch"

    exp_tool = ExplorerNavigateTool()
    assert exp_tool.tool_id == "explorer.navigate"

    term_tool = TerminalLaunchTool()
    assert term_tool.tool_id == "terminal.launch"

    wf_tool = WorkflowExecuteSequenceTool()
    assert wf_tool.tool_id == "workflow.execute_sequence"


def test_uia_list_windows_execution():
    desktop = MagicMock()
    desktop.window_controller.list_windows.return_value = [
        MagicMock(
            hwnd=101,
            title="Test Window",
            process_name="test.exe",
            pid=1234,
            is_visible=True,
            is_iconic=False,
        )
    ]

    tool = UiaListWindowsTool(desktop_controller=desktop)
    res = tool.execute({"max_results": 10})

    assert res.success
    assert res.data["count"] == 1
    assert res.data["windows"][0]["title"] == "Test Window"
