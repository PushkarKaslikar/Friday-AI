"""Clipboard Management Tools for Friday AI Assistant."""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory
from app.tools.execution.result_normalizer import SensitiveDataSanitizer

if TYPE_CHECKING:
    from app.automation.desktop.desktop_controller import DesktopController


class ClipboardGetContentInput(BaseModel):
    max_characters: int = Field(
        default=2000, ge=10, le=10000, description="Maximum characters to read"
    )


class ClipboardGetContentTool(BaseTool):
    """Tool for reading text from system clipboard."""

    def __init__(
        self, desktop_controller: Optional["DesktopController"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="clipboard.get_content",
            name="ClipboardGetContent",
            display_name="Read Clipboard Text",
            description="Reads and returns text from the system clipboard with secret masking protection.",
            category=ToolCategory.CLIPBOARD,
            tags=["clipboard", "read", "text"],
            input_schema=ClipboardGetContentInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_CLIPBOARD],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller

    def run_tool(
        self, validated_input: ClipboardGetContentInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {
                "status": "SUCCESS",
                "text": "",
                "character_count": 0,
                "simulated": True,
            }

        cb_res = self.desktop_controller.clipboard_manager.read_text(
            max_characters=validated_input.max_characters
        )
        sanitized = SensitiveDataSanitizer.sanitize_text(cb_res.text)

        return {
            "status": "SUCCESS" if cb_res.is_success else "FAILED",
            "text": sanitized,
            "character_count": len(cb_res.text),
            "is_masked": sanitized != cb_res.text,
        }


class ClipboardSetContentInput(BaseModel):
    text: str = Field(description="Text string to write into system clipboard")


class ClipboardSetContentTool(BaseTool):
    """Tool for writing text to system clipboard."""

    def __init__(
        self, desktop_controller: Optional["DesktopController"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="clipboard.set_content",
            name="ClipboardSetContent",
            display_name="Write Clipboard Text",
            description="Sets the system clipboard to the specified text payload.",
            category=ToolCategory.CLIPBOARD,
            tags=["clipboard", "write", "text"],
            input_schema=ClipboardSetContentInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_CLIPBOARD],
            idempotent=True,
        )
        super().__init__(metadata)
        self.desktop_controller = desktop_controller

    def run_tool(
        self, validated_input: ClipboardSetContentInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.desktop_controller:
            return {
                "status": "SUCCESS",
                "character_count": len(validated_input.text),
                "simulated": True,
            }

        cb_res = self.desktop_controller.clipboard_manager.write_text(
            validated_input.text
        )
        return {
            "status": "SUCCESS" if cb_res.is_success else "FAILED",
            "character_count": len(validated_input.text),
            "error": cb_res.error_message if not cb_res.is_success else None,
        }
