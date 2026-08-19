"""File Explorer Automation Tools for Friday AI Assistant."""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory

if TYPE_CHECKING:
    from app.automation.apps.apps_controller import ApplicationAdapterManager
    from app.automation.apps.explorer_adapter import ExplorerAdapter


class ExplorerNavigateInput(BaseModel):
    path: str = Field(
        description="Target directory or folder path to navigate Explorer to"
    )


class ExplorerNavigateTool(BaseTool):
    """Tool for navigating File Explorer window to a directory path."""

    def __init__(
        self, app_manager: Optional["ApplicationAdapterManager"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="explorer.navigate",
            name="ExplorerNavigate",
            display_name="Navigate File Explorer",
            description="Navigates File Explorer UI window to the specified target folder path.",
            category=ToolCategory.FILES,
            tags=["explorer", "navigate", "folder", "path"],
            input_schema=ExplorerNavigateInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_READ],
            idempotent=True,
        )
        super().__init__(metadata)
        self.app_manager = app_manager

    def run_tool(
        self, validated_input: ExplorerNavigateInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.app_manager:
            return {
                "status": "SUCCESS",
                "target_path": validated_input.path,
                "simulated": True,
            }

        exp_adapter: ExplorerAdapter | None = self.app_manager.get_adapter("explorer")
        if exp_adapter:
            res = exp_adapter.navigate_to(validated_input.path)
            return {
                "status": res.status,
                "current_location": res.current_location,
                "message": res.message,
            }

        return {
            "status": "SUCCESS",
            "target_path": validated_input.path,
            "simulated": True,
        }


class ExplorerOpenItemInput(BaseModel):
    item_name: str = Field(
        description="File or folder item name in active Explorer view to open"
    )


class ExplorerOpenItemTool(BaseTool):
    """Tool for opening a selected item inside File Explorer."""

    def __init__(
        self, app_manager: Optional["ApplicationAdapterManager"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="explorer.open_item",
            name="ExplorerOpenItem",
            display_name="Open Explorer Item",
            description="Opens a file or subfolder item currently visible inside File Explorer.",
            category=ToolCategory.FILES,
            tags=["explorer", "open", "file", "item"],
            input_schema=ExplorerOpenItemInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_READ],
            idempotent=True,
        )
        super().__init__(metadata)
        self.app_manager = app_manager

    def run_tool(
        self, validated_input: ExplorerOpenItemInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.app_manager:
            return {
                "status": "SUCCESS",
                "opened_item": validated_input.item_name,
                "simulated": True,
            }

        exp_adapter: ExplorerAdapter | None = self.app_manager.get_adapter("explorer")
        if exp_adapter:
            res = exp_adapter.open_item(validated_input.item_name)
            return {
                "status": res.status,
                "opened_item": validated_input.item_name,
                "message": res.message,
            }

        return {
            "status": "SUCCESS",
            "opened_item": validated_input.item_name,
            "simulated": True,
        }
