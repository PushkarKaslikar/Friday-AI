"""Application management tools for opening, closing, and querying desktop application status."""

import os
import shutil
import subprocess
from typing import Any

import psutil
from pydantic import BaseModel, Field

from app.logging import logger
from app.platform.process.process_manager import ProcessManager
from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory
from app.tools.models.errors import ToolErrorCode, ToolExecutionError

KNOWN_APP_EXECUTABLES: dict[str, str] = {
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "browser": "chrome.exe",
    "notepad": "notepad.exe",
    "notes": "notepad.exe",
    "calculator": "calc.exe",
    "calculate": "calc.exe",
    "calc": "calc.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "this pc": "explorer.exe",
    "my computer": "explorer.exe",
    "edge": "msedge.exe",
    "msedge": "msedge.exe",
    "paint": "mspaint.exe",
    "mspaint": "mspaint.exe",
    "code": "code.cmd",
    "vscode": "code.cmd",
    "vs code": "code.cmd",
    "microsoft store": "ms-windows-store:",
    "store": "ms-windows-store:",
    "windows store": "ms-windows-store:",
    "settings": "ms-settings:",
    "task manager": "taskmgr.exe",
    "taskmgr": "taskmgr.exe",
    "control panel": "control.exe",
    "control": "control.exe",
}


# 1. Open Application Tool
class OpenApplicationInput(BaseModel):
    """Input parameters for OpenApplicationTool."""

    application: str = Field(
        description="Application name (e.g. 'chrome', 'notepad') or executable path"
    )


class OpenApplicationTool(BaseTool):
    """Tool launching a Windows application by name or path."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.open_application",
            name="open_application",
            display_name="Open Application",
            description="Launches a specified Windows application (e.g. 'chrome', 'notepad', 'calculator').",
            category=ToolCategory.WINDOWS,
            tags=["app", "open", "launch", "windows"],
            input_schema=OpenApplicationInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.PROCESS_CONTROL],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: OpenApplicationInput = validated_input  # type: ignore
        app_name_raw = inp.application.strip().lower()

        # Check known alias dictionary
        exe_name = KNOWN_APP_EXECUTABLES.get(app_name_raw, app_name_raw)

        # Handle URI schemes directly (e.g., ms-windows-store:, ms-settings:)
        if ":" in exe_name and not os.path.exists(exe_name):
            try:
                os.startfile(exe_name)
                logger.info(f"OpenApplicationTool: Protocol launched '{exe_name}'.")
                return {"launched": True, "application": exe_name, "path": "protocol_uri"}
            except Exception as exc:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.EXECUTION_FAILED,
                    message=f"Failed to launch protocol URI '{exe_name}': {exc}",
                    tool_id=self.tool_id,
                ) from exc

        # Check path lookup
        target_path = shutil.which(exe_name) or shutil.which(f"{exe_name}.exe")

        if not target_path and os.path.exists(inp.application):
            target_path = inp.application

        if not target_path:
            # Fallback to system shell launch for protocol/alias
            try:
                os.startfile(exe_name)
                logger.info(
                    f"OpenApplicationTool: Launched via os.startfile('{exe_name}')."
                )
                return {
                    "launched": True,
                    "application": exe_name,
                    "path": "shell_resolved",
                }
            except Exception as exc:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.DEPENDENCY_UNAVAILABLE,
                    message=f"Application '{inp.application}' could not be resolved or launched: {exc}",
                    tool_id=self.tool_id,
                ) from exc

        try:
            subprocess.Popen([target_path], close_fds=True)
            logger.info(f"OpenApplicationTool: Launched '{target_path}'.")
            return {"launched": True, "application": exe_name, "path": target_path}
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to launch application '{target_path}': {exc}",
                tool_id=self.tool_id,
            ) from exc


# 2. Close Application Tool
class CloseApplicationInput(BaseModel):
    """Input parameters for CloseApplicationTool."""

    application_name: str = Field(
        description="Process/Application name to close (e.g. 'notepad.exe' or 'chrome')"
    )


class CloseApplicationTool(BaseTool):
    """Tool gracefully terminating a target application process."""

    def __init__(self, process_manager: ProcessManager | None = None) -> None:
        meta = ToolMetadata(
            tool_id="system.close_application",
            name="close_application",
            display_name="Close Application",
            description="Gracefully closes running instances of a target application process.",
            category=ToolCategory.WINDOWS,
            tags=["app", "close", "terminate", "windows"],
            input_schema=CloseApplicationInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.PROCESS_CONTROL],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.process_manager = process_manager or ProcessManager()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: CloseApplicationInput = validated_input  # type: ignore
        target = inp.application_name.strip().lower()
        if not target.endswith(".exe") and not target.endswith(".cmd"):
            target += ".exe"

        closed_pids = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == target:
                    pid = proc.info["pid"]
                    proc.terminate()
                    closed_pids.append(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if not closed_pids:
            return {
                "closed": False,
                "message": f"No running instances of '{target}' were found.",
            }

        return {"closed": True, "application": target, "closed_pids": closed_pids}


# 3. Application Status Tool
class ApplicationStatusInput(BaseModel):
    """Input parameters for ApplicationStatusTool."""

    application_name: str = Field(description="Application name or executable string")


class ApplicationStatusTool(BaseTool):
    """Tool checking if a target application is currently running."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.application_status",
            name="application_status",
            display_name="Check Application Status",
            description="Queries whether an application is currently running and returns active PIDs.",
            category=ToolCategory.WINDOWS,
            tags=["app", "status", "running", "windows"],
            input_schema=ApplicationStatusInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.PROCESS_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: ApplicationStatusInput = validated_input  # type: ignore
        target = inp.application_name.strip().lower()
        query = KNOWN_APP_EXECUTABLES.get(target, target)

        if not query.endswith(".exe") and not query.endswith(".cmd"):
            query += ".exe"

        running_pids = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == query:
                    running_pids.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "application": target,
            "executable": query,
            "is_running": len(running_pids) > 0,
            "running_count": len(running_pids),
            "pids": running_pids,
        }
