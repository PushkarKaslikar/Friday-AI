"""Physical Mouse & Keyboard Input Tools for Friday AI Assistant."""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory
from app.tools.execution.result_normalizer import SensitiveDataSanitizer

if TYPE_CHECKING:
    from app.automation.input.input_engine import InputEngine


class InputMouseClickInput(BaseModel):
    x: int | None = Field(default=None, description="Screen X coordinate")
    y: int | None = Field(default=None, description="Screen Y coordinate")
    button: str = Field(
        default="left", description="Mouse button (left, right, middle)"
    )
    clicks: int = Field(
        default=1, ge=1, le=3, description="Click count (1=single, 2=double)"
    )


class InputMouseClickTool(BaseTool):
    """Tool for triggering human-like mouse click operations."""

    def __init__(self, input_engine: Optional["InputEngine"] = None) -> None:
        metadata = ToolMetadata(
            tool_id="input.mouse_click",
            name="InputMouseClick",
            display_name="Mouse Click Operation",
            description="Triggers a mouse click at specified screen coordinates or current cursor position.",
            category=ToolCategory.INPUT,
            tags=["input", "mouse", "click"],
            input_schema=InputMouseClickInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_INPUT],
            idempotent=False,
        )
        super().__init__(metadata)
        self.input_engine = input_engine

    def run_tool(
        self, validated_input: InputMouseClickInput, command_id: str = ""
    ) -> dict[str, Any]:
        if self.input_engine:
            res = self.input_engine.click(
                x=validated_input.x,
                y=validated_input.y,
                button=validated_input.button,
                clicks=validated_input.clicks,
            )
            return {
                "status": "SUCCESS" if res.is_success else "FAILED",
                "x": validated_input.x,
                "y": validated_input.y,
                "button": validated_input.button,
                "error": res.error_message if not res.is_success else None,
            }
        return {
            "status": "SUCCESS",
            "x": validated_input.x,
            "y": validated_input.y,
            "button": validated_input.button,
            "simulated": True,
        }


class InputTypeTextInput(BaseModel):
    text: str = Field(description="Text string to type")
    wpm: int = Field(
        default=60, ge=10, le=200, description="Typing speed in Words Per Minute"
    )


class InputTypeTextTool(BaseTool):
    """Tool for typing text into the focused application."""

    def __init__(self, input_engine: Optional["InputEngine"] = None) -> None:
        metadata = ToolMetadata(
            tool_id="input.type_text",
            name="InputTypeText",
            display_name="Type Text Operation",
            description="Types text into the currently active or focused application input field.",
            category=ToolCategory.INPUT,
            tags=["input", "keyboard", "type", "text"],
            input_schema=InputTypeTextInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_INPUT],
            idempotent=False,
        )
        super().__init__(metadata)
        self.input_engine = input_engine

    def run_tool(
        self, validated_input: InputTypeTextInput, command_id: str = ""
    ) -> dict[str, Any]:
        masked_text = SensitiveDataSanitizer.sanitize_text(validated_input.text)

        if self.input_engine:
            res = self.input_engine.type_text(
                validated_input.text, wpm=validated_input.wpm
            )
            return {
                "status": "SUCCESS" if res.is_success else "FAILED",
                "character_count": len(validated_input.text),
                "text_summary": masked_text,
                "error": res.error_message if not res.is_success else None,
            }
        return {
            "status": "SUCCESS",
            "character_count": len(validated_input.text),
            "text_summary": masked_text,
            "simulated": True,
        }


class InputPressHotkeyInput(BaseModel):
    keys: list[str] = Field(
        description="Combination list of key names (e.g. ['ctrl', 'c'] or ['alt', 'tab'])"
    )


class InputPressHotkeyTool(BaseTool):
    """Tool for pressing a keyboard hotkey combination."""

    def __init__(self, input_engine: Optional["InputEngine"] = None) -> None:
        metadata = ToolMetadata(
            tool_id="input.press_hotkey",
            name="InputPressHotkey",
            display_name="Press Hotkey Combination",
            description="Executes a multi-key keyboard hotkey shortcut combination.",
            category=ToolCategory.INPUT,
            tags=["input", "keyboard", "hotkey", "shortcut"],
            input_schema=InputPressHotkeyInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_INPUT],
            idempotent=False,
        )
        super().__init__(metadata)
        self.input_engine = input_engine

    def run_tool(
        self, validated_input: InputPressHotkeyInput, command_id: str = ""
    ) -> dict[str, Any]:
        if self.input_engine and validated_input.keys:
            res = self.input_engine.hotkey(*validated_input.keys)
            return {
                "status": "SUCCESS" if res.is_success else "FAILED",
                "keys": validated_input.keys,
                "error": res.error_message if not res.is_success else None,
            }
        return {"status": "SUCCESS", "keys": validated_input.keys, "simulated": True}
