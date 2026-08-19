"""Phase 6.6 Automation Tool Suite Package."""

from app.tools.builtin.automation.application_tools import (
    ApplicationAttachTool,
    ApplicationLaunchTool,
    ApplicationStatusTool,
)
from app.tools.builtin.automation.clipboard_tools import (
    ClipboardGetContentTool,
    ClipboardSetContentTool,
)
from app.tools.builtin.automation.diagnostics import AutomationToolDiagnostics
from app.tools.builtin.automation.explorer_tools import (
    ExplorerNavigateTool,
    ExplorerOpenItemTool,
)
from app.tools.builtin.automation.input_tools import (
    InputMouseClickTool,
    InputPressHotkeyTool,
    InputTypeTextTool,
)
from app.tools.builtin.automation.metrics import AutomationToolMetrics
from app.tools.builtin.automation.screen_tools import (
    ScreenCaptureTool,
    ScreenListMonitorsTool,
)
from app.tools.builtin.automation.terminal_tools import (
    TerminalLaunchTool,
    TerminalReadOutputTool,
)
from app.tools.builtin.automation.uia_tools import (
    UiaFindElementTool,
    UiaInspectWindowTool,
    UiaListWindowsTool,
)
from app.tools.builtin.automation.window_tools import (
    WindowFocusTool,
    WindowListOpenTool,
    WindowMaximizeTool,
    WindowSnapTool,
)
from app.tools.builtin.automation.workflow_tools import WorkflowExecuteSequenceTool

__all__ = [
    "ApplicationAttachTool",
    "ApplicationLaunchTool",
    "ApplicationStatusTool",
    "AutomationToolDiagnostics",
    "AutomationToolMetrics",
    "ClipboardGetContentTool",
    "ClipboardSetContentTool",
    "ExplorerNavigateTool",
    "ExplorerOpenItemTool",
    "InputMouseClickTool",
    "InputPressHotkeyTool",
    "InputTypeTextTool",
    "ScreenCaptureTool",
    "ScreenListMonitorsTool",
    "TerminalLaunchTool",
    "TerminalReadOutputTool",
    "UiaFindElementTool",
    "UiaInspectWindowTool",
    "UiaListWindowsTool",
    "WindowFocusTool",
    "WindowListOpenTool",
    "WindowMaximizeTool",
    "WindowSnapTool",
    "WorkflowExecuteSequenceTool",
]
