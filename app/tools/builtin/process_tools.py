"""Process management tools for process listing, process inspection, and protected process termination."""

from typing import Any

import psutil
from pydantic import BaseModel, Field

from app.platform.process.process_manager import ProcessManager
from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory
from app.tools.models.errors import ToolErrorCode, ToolExecutionError

PROTECTED_PROCESSES: set[str] = {
    "system",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
    "svchost.exe",
    "fontdrvhost.exe",
    "sihost.exe",
}


# 1. Process List Tool
class ProcessListInput(BaseModel):
    """Input parameters for ProcessListTool."""

    limit: int = Field(
        default=50, ge=1, le=500, description="Maximum processes to return"
    )


class ProcessListTool(BaseTool):
    """Tool querying system active processes."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="process.list",
            name="list_processes",
            display_name="List Processes",
            description="Queries active running processes with PID, process name, CPU utilization %, and RAM usage MB.",
            category=ToolCategory.PROCESS,
            tags=["process", "list", "ps", "system"],
            input_schema=ProcessListInput,
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
        inp: ProcessListInput = validated_input  # type: ignore
        processes = []
        mb = 1024 * 1024

        for proc in psutil.process_iter(["pid", "name", "memory_info", "status"]):
            try:
                mem_mb = (
                    round(proc.info["memory_info"].rss / mb, 2)
                    if proc.info["memory_info"]
                    else 0.0
                )
                processes.append(
                    {
                        "pid": proc.info["pid"],
                        "name": proc.info["name"] or "unknown",
                        "status": proc.info["status"],
                        "memory_mb": mem_mb,
                    }
                )
                if len(processes) >= inp.limit:
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {"process_count": len(processes), "processes": processes}


# 2. Process Info Tool
class ProcessInfoInput(BaseModel):
    """Input parameters for ProcessInfoTool."""

    pid: int = Field(description="Target Process ID (PID)")


class ProcessInfoTool(BaseTool):
    """Tool querying detailed information for a specific Process ID."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="process.get_info",
            name="get_process_info",
            display_name="Get Process Information",
            description="Queries detailed process metadata (name, status, CPU, memory, thread count, created time) for a target PID.",
            category=ToolCategory.PROCESS,
            tags=["process", "info", "pid", "system"],
            input_schema=ProcessInfoInput,
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
        inp: ProcessInfoInput = validated_input  # type: ignore
        pid = inp.pid

        try:
            proc = psutil.Process(pid)
            mem_info = proc.memory_info()
            mb = 1024 * 1024
            return {
                "pid": proc.pid,
                "name": proc.name(),
                "status": proc.status(),
                "create_time": proc.create_time(),
                "num_threads": proc.num_threads(),
                "memory_rss_mb": round(mem_info.rss / mb, 2),
                "memory_vms_mb": round(mem_info.vms / mb, 2),
                "cpu_percent": proc.cpu_percent(interval=0.05),
                "exe_path": proc.exe() if hasattr(proc, "exe") else "",
            }
        except psutil.NoSuchProcess as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Process with PID {pid} does not exist.",
                tool_id=self.tool_id,
            ) from exc
        except psutil.AccessDenied as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.PERMISSION_DENIED,
                message=f"Access denied to process PID {pid}: {exc}",
                tool_id=self.tool_id,
            ) from exc


# 3. Process Running Tool
class ProcessRunningInput(BaseModel):
    """Input parameters for ProcessRunningTool."""

    process_identifier: str = Field(
        description="Process name (e.g. 'notepad.exe') or PID integer as string"
    )


class ProcessRunningTool(BaseTool):
    """Tool checking whether a target process is running."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="process.is_running",
            name="is_running",
            display_name="Check Process Running",
            description="Checks if a target process name or PID is currently active.",
            category=ToolCategory.PROCESS,
            tags=["process", "running", "status", "system"],
            input_schema=ProcessRunningInput,
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
        inp: ProcessRunningInput = validated_input  # type: ignore
        target = inp.process_identifier.strip().lower()

        is_pid = target.isdigit()
        pid_target = int(target) if is_pid else None

        pids = []
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if (
                    is_pid
                    and proc.info["pid"] == pid_target
                    or proc.info["name"]
                    and proc.info["name"].lower() == target
                ):
                    pids.append(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return {
            "query": target,
            "is_running": len(pids) > 0,
            "running_count": len(pids),
            "pids": pids,
        }


# 4. Terminate Process Tool
class TerminateProcessInput(BaseModel):
    """Input parameters for TerminateProcessTool."""

    pid: int = Field(description="Target Process ID (PID) to terminate")


class TerminateProcessTool(BaseTool):
    """Tool terminating a specific process ID with Protected Process Policy protection."""

    def __init__(self, process_manager: ProcessManager | None = None) -> None:
        meta = ToolMetadata(
            tool_id="process.terminate",
            name="terminate_process",
            display_name="Terminate Process",
            description="Terminates a target process ID with Protected System Process Policy protection.",
            category=ToolCategory.PROCESS,
            tags=["process", "terminate", "kill", "system"],
            input_schema=TerminateProcessInput,
            risk_level=ToolRiskLevel.HIGH,
            permissions=[ToolPermission.PROCESS_CONTROL],
            confirmation_required=True,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.process_manager = process_manager or ProcessManager()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: TerminateProcessInput = validated_input  # type: ignore
        pid = inp.pid

        try:
            proc = psutil.Process(pid)
            proc_name = proc.name().lower()

            if proc_name in PROTECTED_PROCESSES:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.PERMISSION_DENIED,
                    message=f"Protected Process Policy violation: Cannot terminate critical Windows process '{proc_name}' (PID: {pid}).",
                    tool_id=self.tool_id,
                )

            proc.terminate()
            return {"terminated": True, "pid": pid, "process_name": proc_name}
        except psutil.NoSuchProcess as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Process PID {pid} does not exist.",
                tool_id=self.tool_id,
            ) from exc
        except psutil.AccessDenied as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.PERMISSION_DENIED,
                message=f"Access denied: Failed to terminate PID {pid}: {exc}",
                tool_id=self.tool_id,
            ) from exc
