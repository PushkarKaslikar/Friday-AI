"""Window Management Tools for Friday AI Assistant."""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory

if TYPE_CHECKING:
    from app.automation.desktop.desktop_controller import DesktopController


class WindowListOpenInput(BaseModel):
    max_results: int = Field(
        default=50, ge=1, le=100, description="Maximum open windows to return"
    )


class WindowListOpenTool(BaseTool):
    """Tool for listing active open desktop windows."""

    def __init__(
        self, desktop_controller: Optional["DesktopController"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="window.list_open",
            name="WindowListOpen",
            display_name="List Open Windows",
            description="Returns a list of all currently open desktop windows, titles, geometry, and active state.",
            category=ToolCategory.WINDOWS,
            tags=["window", "list", "open", "desktop"],
            input_schema=WindowListOpenInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.AUTOMATION_READ],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller

    def run_tool(
        self, validated_input: WindowListOpenInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {"status": "SUCCESS", "windows": [], "count": 0}

        wins = self.desktop_controller.window_controller.list_windows()
        res = []
        for w in wins[: validated_input.max_results]:
            res.append(
                {
                    "hwnd": w.hwnd,
                    "title": w.title,
                    "process_name": w.process_name,
                    "geometry": {
                        "x": w.left,
                        "y": w.top,
                        "width": w.width,
                        "height": w.height,
                    },
                    "is_active": w.is_active,
                }
            )

        return {"status": "SUCCESS", "windows": res, "count": len(res)}


class WindowFocusInput(BaseModel):
    target: str = Field(
        description="Window title, process name substring, or HWND integer to focus"
    )


class WindowFocusTool(BaseTool):
    """Tool for bringing a window to the foreground and focusing it."""

    def __init__(
        self, desktop_controller: Optional["DesktopController"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="window.focus",
            name="WindowFocus",
            display_name="Focus Window",
            description="Brings the target application window to the foreground and gives it input focus.",
            category=ToolCategory.WINDOWS,
            tags=["window", "focus", "foreground"],
            input_schema=WindowFocusInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_WINDOW],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller

    def run_tool(
        self, validated_input: WindowFocusInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {
                "status": "SUCCESS",
                "target": validated_input.target,
                "simulated": True,
            }

        wins = self.desktop_controller.window_controller.list_windows()
        target_win = None
        for w in wins:
            if (
                str(w.hwnd) == validated_input.target
                or validated_input.target.lower() in w.title.lower()
                or validated_input.target.lower() in w.process_name.lower()
            ):
                target_win = w
                break

        if not target_win:
            return {"status": "WINDOW_NOT_FOUND", "target": validated_input.target}

        focused = self.desktop_controller.window_controller.focus_window(
            target_win.hwnd
        )
        return {
            "status": "SUCCESS" if focused else "FAILED",
            "hwnd": target_win.hwnd,
            "title": target_win.title,
        }


class WindowMaximizeInput(BaseModel):
    target: str = Field(
        description="Window title, process name substring, or HWND integer to maximize"
    )


class WindowMaximizeTool(BaseTool):
    """Tool for maximizing a target window."""

    def __init__(
        self, desktop_controller: Optional["DesktopController"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="window.maximize",
            name="WindowMaximize",
            display_name="Maximize Window",
            description="Maximizes the target window across its monitor workarea.",
            category=ToolCategory.WINDOWS,
            tags=["window", "maximize"],
            input_schema=WindowMaximizeInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_WINDOW],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller

    def run_tool(
        self, validated_input: WindowMaximizeInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {
                "status": "SUCCESS",
                "target": validated_input.target,
                "simulated": True,
            }

        wins = self.desktop_controller.window_controller.list_windows()
        target_win = None
        for w in wins:
            if (
                str(w.hwnd) == validated_input.target
                or validated_input.target.lower() in w.title.lower()
                or validated_input.target.lower() in w.process_name.lower()
            ):
                target_win = w
                break

        if not target_win:
            return {"status": "WINDOW_NOT_FOUND", "target": validated_input.target}

        res = self.desktop_controller.window_controller.maximize_window(target_win.hwnd)
        return {
            "status": "SUCCESS" if res else "FAILED",
            "hwnd": target_win.hwnd,
            "title": target_win.title,
        }


class WindowSnapInput(BaseModel):
    target: str = Field(
        description="Window title, process name substring, or HWND integer to snap"
    )
    position: str = Field(
        default="left",
        description="Snap position (left, right, top_left, top_right, etc.)",
    )


class WindowSnapTool(BaseTool):
    """Tool for snapping a window to a monitor tile location."""

    def __init__(
        self, desktop_controller: Optional["DesktopController"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="window.snap",
            name="WindowSnap",
            display_name="Snap Window Layout",
            description="Snaps a target window to a specified monitor side or grid location.",
            category=ToolCategory.WINDOWS,
            tags=["window", "snap", "arrange"],
            input_schema=WindowSnapInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_WINDOW],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller

    def run_tool(
        self, validated_input: WindowSnapInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {
                "status": "SUCCESS",
                "target": validated_input.target,
                "position": validated_input.position,
                "simulated": True,
            }

        wins = self.desktop_controller.window_controller.list_windows()
        target_win = None
        for w in wins:
            if (
                str(w.hwnd) == validated_input.target
                or validated_input.target.lower() in w.title.lower()
                or validated_input.target.lower() in w.process_name.lower()
            ):
                target_win = w
                break

        if not target_win:
            return {"status": "WINDOW_NOT_FOUND", "target": validated_input.target}

        res = self.desktop_controller.window_controller.snap_window(
            target_win.hwnd, validated_input.position
        )
        return {
            "status": "SUCCESS" if res else "FAILED",
            "hwnd": target_win.hwnd,
            "position": validated_input.position,
        }
