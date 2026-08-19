"""Terminal Automation Tools for Friday AI Assistant."""

from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory
from app.tools.execution.result_normalizer import SensitiveDataSanitizer

if TYPE_CHECKING:
    from app.automation.apps.apps_controller import ApplicationAdapterManager
    from app.automation.apps.terminal_adapter import TerminalAdapter


class TerminalLaunchInput(BaseModel):
    terminal_type: str = Field(
        default="cmd", description="Terminal family type (cmd, powershell, wt)"
    )
    working_directory: str | None = Field(
        default=None, description="Initial working directory path"
    )


class TerminalLaunchTool(BaseTool):
    """Tool for launching or attaching a terminal subsystem session."""

    def __init__(
        self, app_manager: Optional["ApplicationAdapterManager"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="terminal.launch",
            name="TerminalLaunch",
            display_name="Launch Terminal Subsystem",
            description="Launches a terminal subsystem window (cmd, powershell, windows terminal) at a specified working directory.",
            category=ToolCategory.PROCESS,
            tags=["terminal", "launch", "cmd", "powershell"],
            input_schema=TerminalLaunchInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_TERMINAL],
            idempotent=False,
        )
        super().__init__(metadata)
        self.app_manager = app_manager

    def run_tool(
        self, validated_input: TerminalLaunchInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.app_manager:
            return {
                "status": "SUCCESS",
                "terminal_type": validated_input.terminal_type,
                "simulated": True,
            }

        from app.automation.apps.models import TerminalType

        term_adapter: TerminalAdapter | None = self.app_manager.get_adapter("terminal")
        if term_adapter:
            ttype = TerminalType.CMD
            if validated_input.terminal_type.lower() == "powershell":
                ttype = TerminalType.POWERSHELL
            elif validated_input.terminal_type.lower() in ("wt", "windows_terminal"):
                ttype = TerminalType.WINDOWS_TERMINAL

            res = term_adapter.launch(
                terminal_type=ttype, cwd=validated_input.working_directory
            )
            return {
                "status": res.status if hasattr(res, "status") else "SUCCESS",
                "terminal_type": validated_input.terminal_type,
                "hwnd": res.hwnd if hasattr(res, "hwnd") else 0,
            }

        return {
            "status": "SUCCESS",
            "terminal_type": validated_input.terminal_type,
            "simulated": True,
        }


class TerminalReadOutputInput(BaseModel):
    max_characters: int = Field(
        default=2000,
        ge=100,
        le=4096,
        description="Maximum output buffer characters to read",
    )


class TerminalReadOutputTool(BaseTool):
    """Tool for reading text output from active terminal buffer."""

    def __init__(
        self, app_manager: Optional["ApplicationAdapterManager"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="terminal.read_output",
            name="TerminalReadOutput",
            display_name="Read Terminal Output",
            description="Reads bounded text from the active terminal buffer with credential masking.",
            category=ToolCategory.PROCESS,
            tags=["terminal", "read", "output", "buffer"],
            input_schema=TerminalReadOutputInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.AUTOMATION_TERMINAL],
            idempotent=True,
        )
        super().__init__(metadata)
        self.app_manager = app_manager

    def run_tool(
        self, validated_input: TerminalReadOutputInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.app_manager:
            return {
                "status": "SUCCESS",
                "output": "",
                "character_count": 0,
                "simulated": True,
            }

        term_adapter: TerminalAdapter | None = self.app_manager.get_adapter("terminal")
        if term_adapter:
            out = term_adapter.read_output(
                max_characters=validated_input.max_characters
            )
            sanitized = SensitiveDataSanitizer.sanitize_text(out.text)
            return {
                "status": "SUCCESS" if out.is_success else "FAILED",
                "output": sanitized,
                "character_count": len(out.text),
                "is_masked": sanitized != out.text,
            }

        return {
            "status": "SUCCESS",
            "output": "",
            "character_count": 0,
            "simulated": True,
        }
