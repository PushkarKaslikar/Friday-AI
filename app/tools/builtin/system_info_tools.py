"""System Information tools querying CPU, RAM, Disk, Windows OS, Uptime, and Current User metadata."""

import getpass
import os
import platform
import time
from typing import Any

import psutil
from pydantic import BaseModel, Field

from app.platform.info.system_info import SystemInfo as SystemInfoService
from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory


# 1. CPU Info Tool
class CpuInfoInput(BaseModel):
    """Input parameters for CpuInfoTool."""

    include_per_cpu: bool = Field(
        default=False, description="Whether to include per-core usage %"
    )


class CpuInfoTool(BaseTool):
    """Tool querying system CPU hardware metadata and utilization."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.get_cpu_info",
            name="get_cpu_info",
            display_name="Get CPU Information",
            description="Queries CPU hardware model, physical/logical core counts, and current CPU utilization %.",
            category=ToolCategory.SYSTEM,
            tags=["cpu", "hardware", "system", "metrics"],
            input_schema=CpuInfoInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.PROCESS_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
            max_retries=2,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: CpuInfoInput = validated_input  # type: ignore
        sys_info = SystemInfoService().get_system_summary()

        data = {
            "processor": platform.processor() or sys_info.get("processor", "x86_64"),
            "physical_cores": sys_info.get("cpu_count_physical")
            or psutil.cpu_count(logical=False)
            or 1,
            "logical_cores": sys_info.get("cpu_count_logical")
            or psutil.cpu_count(logical=True)
            or 1,
            "cpu_freq_mhz": sys_info.get("cpu_freq_mhz", 0.0),
            "total_cpu_percent": psutil.cpu_percent(interval=0.1),
        }
        if inp.include_per_cpu:
            data["per_cpu_percent"] = psutil.cpu_percent(interval=0.1, percpu=True)
        return data


# 2. Memory Info Tool
class MemoryInfoInput(BaseModel):
    """Input parameters for MemoryInfoTool."""


class MemoryInfoTool(BaseTool):
    """Tool querying RAM memory statistics."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.get_memory_info",
            name="get_memory_info",
            display_name="Get Memory Information",
            description="Queries RAM total, used, available memory in GB and usage percentage.",
            category=ToolCategory.SYSTEM,
            tags=["ram", "memory", "system", "metrics"],
            input_schema=MemoryInfoInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.PROCESS_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
            max_retries=2,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()

        gb = 1024 * 1024 * 1024
        return {
            "total_gb": round(mem.total / gb, 2),
            "used_gb": round(mem.used / gb, 2),
            "available_gb": round(mem.available / gb, 2),
            "usage_percent": mem.percent,
            "swap_total_gb": round(swap.total / gb, 2),
            "swap_used_gb": round(swap.used / gb, 2),
        }


# 3. Disk Info Tool
class DiskInfoInput(BaseModel):
    """Input parameters for DiskInfoTool."""

    drive_letter: str | None = Field(
        default=None, description="Optional drive letter filter (e.g. 'C:')"
    )


class DiskInfoTool(BaseTool):
    """Tool querying disk partition space and usage."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.get_disk_info",
            name="get_disk_info",
            display_name="Get Disk Information",
            description="Queries disk storage drives, total capacity, free space, and usage percentage.",
            category=ToolCategory.SYSTEM,
            tags=["disk", "storage", "drives", "system"],
            input_schema=DiskInfoInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.FILESYSTEM_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
            max_retries=2,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: DiskInfoInput = validated_input  # type: ignore
        gb = 1024 * 1024 * 1024
        partitions_data = []

        for part in psutil.disk_partitions(all=False):
            if inp.drive_letter and not part.mountpoint.startswith(
                inp.drive_letter.upper()
            ):
                continue
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions_data.append(
                    {
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / gb, 2),
                        "used_gb": round(usage.used / gb, 2),
                        "free_gb": round(usage.free / gb, 2),
                        "usage_percent": usage.percent,
                    }
                )
            except PermissionError:
                continue

        return {"drives": partitions_data}


# 4. Windows Info Tool
class WindowsInfoInput(BaseModel):
    """Input parameters for WindowsInfoTool."""


class WindowsInfoTool(BaseTool):
    """Tool querying Windows OS version and build metadata."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.get_windows_info",
            name="get_windows_info",
            display_name="Get Windows OS Information",
            description="Queries Windows operating system version, release build number, and machine architecture.",
            category=ToolCategory.WINDOWS,
            tags=["windows", "os", "version", "system"],
            input_schema=WindowsInfoInput,
            risk_level=ToolRiskLevel.LOW,
            confirmation_required=False,
            idempotent=True,
            retryable=True,
            max_retries=2,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        sys_summary = SystemInfoService().get_system_summary()
        return {
            "os_name": sys_summary["os_name"],
            "os_version": sys_summary["os_version"],
            "os_release": sys_summary["os_release"],
            "architecture": sys_summary.get("os_architecture", platform.machine()),
            "machine_name": sys_summary["machine_name"],
        }


# 5. Uptime Tool
class UptimeInput(BaseModel):
    """Input parameters for UptimeTool."""


class UptimeTool(BaseTool):
    """Tool querying system boot time and uptime duration."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.get_uptime",
            name="get_uptime",
            display_name="Get System Uptime",
            description="Queries system boot time timestamp and uptime duration in seconds, minutes, and hours.",
            category=ToolCategory.SYSTEM,
            tags=["uptime", "boottime", "system"],
            input_schema=UptimeInput,
            risk_level=ToolRiskLevel.LOW,
            confirmation_required=False,
            idempotent=True,
            retryable=True,
            max_retries=2,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        boot_time = psutil.boot_time()
        uptime_sec = round(time.time() - boot_time, 2)
        return {
            "boot_time": str(
                time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(boot_time))
            ),
            "uptime_seconds": uptime_sec,
            "uptime_minutes": round(uptime_sec / 60, 2),
            "uptime_hours": round(uptime_sec / 3600, 2),
        }


# 6. Current User Tool
class CurrentUserInput(BaseModel):
    """Input parameters for CurrentUserTool."""


class CurrentUserTool(BaseTool):
    """Tool querying safe current user environment metadata."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="system.get_current_user",
            name="get_current_user",
            display_name="Get Current User Info",
            description="Queries current logged in username, machine hostname, and user domain.",
            category=ToolCategory.SYSTEM,
            tags=["user", "account", "system"],
            input_schema=CurrentUserInput,
            risk_level=ToolRiskLevel.LOW,
            confirmation_required=False,
            idempotent=True,
            retryable=True,
            max_retries=2,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        return {
            "username": getpass.getuser(),
            "machine_name": platform.node(),
            "user_domain": os.environ.get("USERDOMAIN", platform.node()),
        }
