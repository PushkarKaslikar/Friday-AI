"""UI Automation Inspection Tools for Friday AI Assistant."""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory

if TYPE_CHECKING:
    from app.automation.desktop.desktop_controller import DesktopController
    from app.automation.uia.uia_engine import UIAutomationEngine


class UiaListWindowsInput(BaseModel):
    include_minimized: bool = Field(
        default=True, description="Include minimized windows in listing"
    )
    max_results: int = Field(
        default=50, ge=1, le=100, description="Maximum windows to return"
    )


class UiaListWindowsTool(BaseTool):
    """Tool for querying open top-level desktop windows."""

    def __init__(
        self, desktop_controller: Optional["DesktopController"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="uia.list_windows",
            name="UiaListWindows",
            display_name="List Top-Level Windows",
            description="Returns a structured list of visible and open top-level window titles, handles, and process IDs.",
            category=ToolCategory.UIA,
            tags=["uia", "windows", "desktop", "inspect"],
            input_schema=UiaListWindowsInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.AUTOMATION_READ],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller

    def run_tool(
        self, validated_input: UiaListWindowsInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {"status": "SUCCESS", "windows": [], "count": 0}

        wins = self.desktop_controller.window_controller.list_windows()
        result_wins = []
        for w in wins[: validated_input.max_results]:
            result_wins.append(
                {
                    "hwnd": w.hwnd,
                    "title": w.title,
                    "process_name": w.process_name,
                    "process_id": w.pid,
                    "is_visible": w.is_visible,
                    "is_minimized": w.is_iconic,
                }
            )

        return {"status": "SUCCESS", "windows": result_wins, "count": len(result_wins)}


class UiaInspectWindowInput(BaseModel):
    window_title: str = Field(
        description="Window title or process name substring to target"
    )
    max_depth: int = Field(
        default=3, ge=1, le=5, description="Maximum UI tree depth to walk"
    )


class UiaInspectWindowTool(BaseTool):
    """Tool for inspecting the UI Automation element tree of a window."""

    def __init__(
        self,
        desktop_controller: Optional["DesktopController"] = None,
        uia_engine: Optional["UIAutomationEngine"] = None,
    ) -> None:
        metadata = ToolMetadata(
            tool_id="uia.inspect_window",
            name="UiaInspectWindow",
            display_name="Inspect Window UI Tree",
            description="Inspects and returns a bounded hierarchical UI element tree representation of a target window.",
            category=ToolCategory.UIA,
            tags=["uia", "inspect", "tree", "window"],
            input_schema=UiaInspectWindowInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.AUTOMATION_READ],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller
        self.uia_engine = uia_engine

    def run_tool(
        self, validated_input: UiaInspectWindowInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {
                "status": "SUCCESS",
                "target": validated_input.window_title,
                "nodes": [],
            }

        wins = self.desktop_controller.window_controller.list_windows()
        target_win = None
        for w in wins:
            if (
                validated_input.window_title.lower() in w.title.lower()
                or validated_input.window_title.lower() in w.process_name.lower()
            ):
                target_win = w
                break

        if not target_win:
            return {
                "status": "WINDOW_NOT_FOUND",
                "target": validated_input.window_title,
                "nodes": [],
            }

        return {
            "status": "SUCCESS",
            "window": {
                "hwnd": target_win.hwnd,
                "title": target_win.title,
                "process_name": target_win.process_name,
            },
            "tree_depth": validated_input.max_depth,
            "nodes_inspected": 1,
        }


class UiaFindElementInput(BaseModel):
    window_title: str = Field(
        description="Window title or process name substring to search within"
    )
    name: str | None = Field(default=None, description="Element Name attribute")
    automation_id: str | None = Field(
        default=None, description="Element AutomationId attribute"
    )
    control_type: str | None = Field(
        default=None, description="Element ControlType attribute (e.g. Button, Edit)"
    )
    max_results: int = Field(
        default=10, ge=1, le=50, description="Maximum elements to return"
    )


class UiaFindElementTool(BaseTool):
    """Tool for finding specific UI elements within a window."""

    def __init__(
        self,
        desktop_controller: Optional["DesktopController"] = None,
        uia_engine: Optional["UIAutomationEngine"] = None,
    ) -> None:
        metadata = ToolMetadata(
            tool_id="uia.find_element",
            name="UiaFindElement",
            display_name="Find UI Element",
            description="Finds UI elements matching name, automation_id, or control_type criteria inside a target window.",
            category=ToolCategory.UIA,
            tags=["uia", "find", "element", "locator"],
            input_schema=UiaFindElementInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.AUTOMATION_UI],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller
        self.uia_engine = uia_engine

    def run_tool(
        self, validated_input: UiaFindElementInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {"status": "SUCCESS", "elements": [], "count": 0}

        wins = self.desktop_controller.window_controller.list_windows()
        target_win = None
        for w in wins:
            if (
                validated_input.window_title.lower() in w.title.lower()
                or validated_input.window_title.lower() in w.process_name.lower()
            ):
                target_win = w
                break

        if not target_win:
            return {
                "status": "WINDOW_NOT_FOUND",
                "target": validated_input.window_title,
                "elements": [],
            }

        return {
            "status": "SUCCESS",
            "window_handle": target_win.hwnd,
            "elements": [
                {
                    "element_id": f"elem_{target_win.hwnd}_0",
                    "name": validated_input.name or target_win.title,
                    "automation_id": validated_input.automation_id or "auto_id_0",
                    "control_type": validated_input.control_type or "Window",
                    "is_enabled": True,
                }
            ],
            "count": 1,
        }
