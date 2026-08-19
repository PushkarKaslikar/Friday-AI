"""Screen Inspection and Capture Tools for Friday AI Assistant."""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory

if TYPE_CHECKING:
    from app.automation.desktop.desktop_controller import DesktopController


class ScreenCaptureInput(BaseModel):
    monitor_index: int | None = Field(
        default=None, description="Optional monitor index to capture"
    )


class ScreenCaptureTool(BaseTool):
    """Tool for capturing screen metadata and local image references."""

    def __init__(
        self, desktop_controller: Optional["DesktopController"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="screen.capture",
            name="ScreenCapture",
            display_name="Capture Desktop Screen",
            description="Captures the desktop screen and returns structured resolution metadata and local capture reference.",
            category=ToolCategory.SCREEN,
            tags=["screen", "capture", "screenshot"],
            input_schema=ScreenCaptureInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_SCREEN],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller

    def run_tool(
        self, validated_input: ScreenCaptureInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {
                "status": "SUCCESS",
                "capture_id": "cap_simulated_0",
                "width": 1920,
                "height": 1080,
                "simulated": True,
            }

        res = self.desktop_controller.capture_screen(
            monitor_id=validated_input.monitor_index
        )
        return {
            "status": res.status,
            "capture_id": res.capture_id,
            "width": res.width,
            "height": res.height,
            "monitor_index": res.monitor_index,
            "timestamp": res.timestamp,
        }


class ScreenListMonitorsInput(BaseModel):
    pass


class ScreenListMonitorsTool(BaseTool):
    """Tool for querying multi-monitor display topology."""

    def __init__(
        self, desktop_controller: Optional["DesktopController"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="screen.list_monitors",
            name="ScreenListMonitors",
            display_name="List Monitor Topology",
            description="Inspects and returns all connected physical monitors, resolutions, and primary display status.",
            category=ToolCategory.SCREEN,
            tags=["screen", "monitors", "topology", "display"],
            input_schema=ScreenListMonitorsInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.AUTOMATION_READ],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller

    def run_tool(
        self, validated_input: ScreenListMonitorsInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {"status": "SUCCESS", "monitors": [], "count": 0}

        mons = self.desktop_controller.monitor_manager.list_monitors()
        res = []
        for m in mons:
            res.append(
                {
                    "device_name": m.device_name,
                    "is_primary": m.is_primary,
                    "bounds": {
                        "x": m.bounds[0],
                        "y": m.bounds[1],
                        "width": m.bounds[2] - m.bounds[0],
                        "height": m.bounds[3] - m.bounds[1],
                    },
                }
            )

        return {"status": "SUCCESS", "monitors": res, "count": len(res)}
