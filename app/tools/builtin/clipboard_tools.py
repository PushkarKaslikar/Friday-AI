"""Clipboard management tools for reading and writing text from Windows system clipboard."""

from typing import Any

from pydantic import BaseModel, Field
from PySide6.QtWidgets import QApplication

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory
from app.tools.models.errors import ToolErrorCode, ToolExecutionError

_MOCK_CLIPBOARD_TEXT: str = ""


# 1. Read Clipboard Tool
class ReadClipboardInput(BaseModel):
    """Input parameters for ReadClipboardTool."""


class ReadClipboardTool(BaseTool):
    """Tool reading plain text contents from Windows clipboard."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="clipboard.read",
            name="read_clipboard",
            display_name="Read Clipboard",
            description="Reads plain text content from the Windows system clipboard.",
            category=ToolCategory.CLIPBOARD,
            tags=["clipboard", "read", "copy", "paste"],
            input_schema=ReadClipboardInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.CLIPBOARD_READ],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        global _MOCK_CLIPBOARD_TEXT
        app = QApplication.instance()
        if app:
            try:
                cb = app.clipboard()
                text = cb.text()
                return {"text": text, "length": len(text)}
            except Exception as exc:  # noqa: BLE001
                _MOCK_CLIPBOARD_TEXT = str(exc)

        return {"text": _MOCK_CLIPBOARD_TEXT, "length": len(_MOCK_CLIPBOARD_TEXT)}


# 2. Write Clipboard Tool
class WriteClipboardInput(BaseModel):
    """Input parameters for WriteClipboardTool."""

    text: str = Field(description="Text string to write to clipboard")


class WriteClipboardTool(BaseTool):
    """Tool writing text content to Windows clipboard."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="clipboard.write",
            name="write_clipboard",
            display_name="Write Clipboard",
            description="Writes text content to the Windows system clipboard.",
            category=ToolCategory.CLIPBOARD,
            tags=["clipboard", "write", "copy"],
            input_schema=WriteClipboardInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.CLIPBOARD_WRITE],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        global _MOCK_CLIPBOARD_TEXT
        inp: WriteClipboardInput = validated_input  # type: ignore
        content = inp.text

        app = QApplication.instance()
        if app:
            try:
                cb = app.clipboard()
                cb.setText(content)
                _MOCK_CLIPBOARD_TEXT = content
                return {"written": True, "length": len(content)}
            except Exception as exc:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.EXECUTION_FAILED,
                    message=f"Failed to write to clipboard: {exc}",
                    tool_id=self.tool_id,
                ) from exc

        _MOCK_CLIPBOARD_TEXT = content
        return {"written": True, "length": len(content)}
