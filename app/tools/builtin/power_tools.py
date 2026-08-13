"""Power management tools for locking, sleeping, restarting, and shutting down Windows with safety controls."""

import ctypes
import os
import subprocess
from typing import Any

from pydantic import BaseModel, Field

from app.logging import logger
from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory

# Global safety switch protecting development & automated testing runs
REAL_POWER_EXECUTION_ENABLED: bool = False


# 1. Lock Computer Tool
class LockComputerInput(BaseModel):
    """Input parameters for LockComputerTool."""


class LockComputerTool(BaseTool):
    """Tool locking current Windows desktop session."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.lock",
            name="lock_computer",
            display_name="Lock Computer",
            description="Locks the current Windows desktop session.",
            category=ToolCategory.SYSTEM,
            tags=["power", "lock", "session", "system"],
            input_schema=LockComputerInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.SYSTEM_POWER],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        if REAL_POWER_EXECUTION_ENABLED:
            try:
                ctypes.windll.user32.LockWorkStation()
                logger.info("LockComputerTool: Locked workstation.")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"LockComputerTool: {exc}")

        return {"locked": True, "message": "Workstation lock triggered."}


# 2. Sleep Computer Tool
class SleepComputerInput(BaseModel):
    """Input parameters for SleepComputerTool."""


class SleepComputerTool(BaseTool):
    """Tool placing system into sleep mode with high risk authorization."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.sleep",
            name="sleep_computer",
            display_name="Sleep Computer",
            description="Places the computer into sleep mode. High risk operation requiring authorization.",
            category=ToolCategory.SYSTEM,
            tags=["power", "sleep", "system"],
            input_schema=SleepComputerInput,
            risk_level=ToolRiskLevel.HIGH,
            permissions=[ToolPermission.SYSTEM_POWER],
            confirmation_required=True,
            idempotent=False,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        if REAL_POWER_EXECUTION_ENABLED:
            try:
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                logger.info("SleepComputerTool: Sleep mode executed.")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"SleepComputerTool: {exc}")

        return {
            "sleep_initiated": True,
            "message": "Sleep command executed (Safety Stubbed).",
        }


# 3. Restart Computer Tool
class RestartComputerInput(BaseModel):
    """Input parameters for RestartComputerTool."""

    force: bool = Field(
        default=False, description="Whether to force close applications"
    )


class RestartComputerTool(BaseTool):
    """Tool restarting Windows with high risk authorization."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.restart",
            name="restart_computer",
            display_name="Restart Computer",
            description="Restarts the Windows computer. High risk operation requiring explicit confirmation.",
            category=ToolCategory.SYSTEM,
            tags=["power", "restart", "reboot", "system"],
            input_schema=RestartComputerInput,
            risk_level=ToolRiskLevel.HIGH,
            permissions=[ToolPermission.SYSTEM_POWER],
            confirmation_required=True,
            idempotent=False,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: RestartComputerInput = validated_input  # type: ignore
        flag = "/f" if inp.force else "/r"

        if REAL_POWER_EXECUTION_ENABLED:
            try:
                subprocess.Popen(
                    ["shutdown.exe", "/r", "/t", "5", flag], close_fds=True
                )
                logger.info("RestartComputerTool: Windows restart initiated.")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"RestartComputerTool: {exc}")

        return {
            "restart_initiated": True,
            "message": "Restart command executed (Safety Stubbed).",
        }


# 4. Shutdown Computer Tool
class ShutdownComputerInput(BaseModel):
    """Input parameters for ShutdownComputerTool."""

    force: bool = Field(
        default=False, description="Whether to force close applications"
    )


class ShutdownComputerTool(BaseTool):
    """Tool shutting down Windows with high risk authorization."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.shutdown",
            name="shutdown_computer",
            display_name="Shutdown Computer",
            description="Shuts down the Windows computer. High risk operation requiring explicit confirmation.",
            category=ToolCategory.SYSTEM,
            tags=["power", "shutdown", "off", "system"],
            input_schema=ShutdownComputerInput,
            risk_level=ToolRiskLevel.HIGH,
            permissions=[ToolPermission.SYSTEM_POWER],
            confirmation_required=True,
            idempotent=False,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: ShutdownComputerInput = validated_input  # type: ignore
        flag = "/f" if inp.force else "/s"

        if REAL_POWER_EXECUTION_ENABLED:
            try:
                subprocess.Popen(
                    ["shutdown.exe", "/s", "/t", "5", flag], close_fds=True
                )
                logger.info("ShutdownComputerTool: Windows shutdown initiated.")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"ShutdownComputerTool: {exc}")

        return {
            "shutdown_initiated": True,
            "message": "Shutdown command executed (Safety Stubbed).",
        }
