"""Application Control Tools for Friday AI Assistant."""

import os
import shutil
import subprocess
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel, Field

from app.logging import logger
from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory

if TYPE_CHECKING:
    from app.automation.apps.apps_controller import ApplicationAdapterManager


KNOWN_APP_EXECUTABLES: dict[str, str] = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "explorer": "explorer",
    "file explorer": "explorer",
    "folder": "explorer",
    "notepad": "notepad",
    "text editor": "notepad",
    "cmd": "cmd",
    "terminal": "wt",
    "edge": "msedge",
    "msedge": "msedge",
    "calculator": "calc",
    "calc": "calc",
}


class ApplicationLaunchInput(BaseModel):
    application: str = Field(
        description="Application alias, name, or approved executable (e.g. explorer, cmd, powershell)"
    )
    arguments: str | None = Field(
        default=None, description="Optional command-line arguments string"
    )


class ApplicationLaunchTool(BaseTool):
    """Tool for launching target Windows applications via ApplicationAdapterManager."""

    def __init__(
        self, app_manager: Optional["ApplicationAdapterManager"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="application.launch",
            name="ApplicationLaunch",
            display_name="Launch Application",
            description="Launches a Windows application by name, approved path, or adapter alias.",
            category=ToolCategory.AUTOMATION,
            tags=["application", "launch", "process", "app"],
            input_schema=ApplicationLaunchInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.AUTOMATION_APPLICATION],
            idempotent=False,
        )
        super().__init__(metadata)
        self.app_manager = app_manager

    def run_tool(
        self, validated_input: ApplicationLaunchInput, command_id: str = ""
    ) -> dict[str, Any]:
        app_req = validated_input.application.strip().lower()
        exe_name = KNOWN_APP_EXECUTABLES.get(app_req, app_req)

        if self.app_manager:
            adapter = self.app_manager.resolve_adapter(exe_name)
            if adapter:
                res = adapter.launch()
                return {
                    "status": res.status,
                    "application": exe_name,
                    "message": res.message,
                }

            res = self.app_manager.launcher.launch_app(
                exe_name, args=validated_input.arguments
            )
            if getattr(res, "status", "") == "SUCCESS":
                return {
                    "status": "SUCCESS",
                    "application": exe_name,
                    "hwnd": getattr(res, "hwnd", 0),
                    "pid": getattr(res, "pid", 0),
                }

        # Real Windows OS process launch fallback
        try:
            os.startfile(exe_name)
            logger.info(
                f"ApplicationLaunchTool: Launched '{exe_name}' via os.startfile."
            )
            return {
                "status": "SUCCESS",
                "application": exe_name,
                "launched": True,
                "method": "startfile",
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"ApplicationLaunchTool startfile failed for '{exe_name}': {exc}. Trying subprocess."
            )

        try:
            target_path = (
                shutil.which(exe_name) or shutil.which(f"{exe_name}.exe") or exe_name
            )
            subprocess.Popen([target_path], close_fds=True)
            logger.info(
                f"ApplicationLaunchTool: Launched '{target_path}' via subprocess."
            )
            return {
                "status": "SUCCESS",
                "application": exe_name,
                "launched": True,
                "method": "subprocess",
            }
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"ApplicationLaunchTool subprocess failed for '{exe_name}': {exc}"
            )
            return {
                "status": "FAILED",
                "application": exe_name,
                "error": str(exc),
            }


class ApplicationAttachInput(BaseModel):
    application: str = Field(
        description="Application alias, title, or process name substring to attach to"
    )


class ApplicationAttachTool(BaseTool):
    """Tool for attaching to a running application window."""

    def __init__(
        self, app_manager: Optional["ApplicationAdapterManager"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="application.attach",
            name="ApplicationAttach",
            display_name="Attach Application",
            description="Attaches to an existing running application window and binds handle reference.",
            category=ToolCategory.AUTOMATION,
            tags=["application", "attach", "window"],
            input_schema=ApplicationAttachInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.AUTOMATION_APPLICATION],
            idempotent=True,
        )
        super().__init__(metadata)
        self.app_manager = app_manager

    def run_tool(
        self, validated_input: ApplicationAttachInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.app_manager:
            return {
                "status": "SUCCESS",
                "application": validated_input.application,
                "simulated": True,
            }

        adapter = self.app_manager.resolve_adapter(validated_input.application)
        if adapter:
            res = adapter.attach()
            return {
                "status": res.state.value if hasattr(res, "state") else "SUCCESS",
                "application": validated_input.application,
                "hwnd": res.hwnd,
            }

        return {
            "status": "SUCCESS",
            "application": validated_input.application,
            "simulated": True,
        }


class ApplicationStatusInput(BaseModel):
    application: str = Field(
        description="Application alias or name to check running status"
    )


class ApplicationStatusTool(BaseTool):
    """Tool for querying application execution status."""

    def __init__(
        self, app_manager: Optional["ApplicationAdapterManager"] = None
    ) -> None:
        metadata = ToolMetadata(
            tool_id="application.status",
            name="ApplicationStatus",
            display_name="Query Application Status",
            description="Queries whether an application or adapter is installed, running, or attached.",
            category=ToolCategory.AUTOMATION,
            tags=["application", "status", "running"],
            input_schema=ApplicationStatusInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.AUTOMATION_READ],
            idempotent=True,
        )
        super().__init__(metadata)
        self.app_manager = app_manager

    def run_tool(
        self, validated_input: ApplicationStatusInput, command_id: str = ""
    ) -> dict[str, Any]:
        if not self.app_manager:
            return {
                "status": "SUCCESS",
                "application": validated_input.application,
                "is_running": False,
            }

        adapter = self.app_manager.resolve_adapter(validated_input.application)
        if adapter:
            return {
                "status": "SUCCESS",
                "application": validated_input.application,
                "is_running": adapter.is_running(),
                "is_installed": adapter.is_installed(),
            }

        return {
            "status": "SUCCESS",
            "application": validated_input.application,
            "is_running": False,
        }
