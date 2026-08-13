"""Native Windows System Information collector using platform, os, and psutil."""

import os
import platform
import sys
from typing import Any

import psutil


class SystemInfo:
    """Collects comprehensive Windows system hardware, OS, and runtime information."""

    def get_system_summary(self) -> dict[str, Any]:
        """Collect complete Windows platform diagnostic dataset.

        Returns:
            dict: Dictionary containing OS, CPU, RAM, Disk, and Display metrics.
        """
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "os_name": "Windows",
            "os_version": platform.version(),
            "os_release": platform.release(),
            "os_architecture": platform.architecture()[0],
            "machine_name": platform.node(),
            "user_name": os.getenv("USERNAME", "unknown"),
            "python_version": sys.version.split()[0],
            "cpu_count_logical": psutil.cpu_count(logical=True),
            "cpu_count_physical": psutil.cpu_count(logical=False),
            "cpu_freq_mhz": (
                round(psutil.cpu_freq().current, 2) if psutil.cpu_freq() else 0.0
            ),
            "total_ram_gb": round(mem.total / (1024**3), 2),
            "available_ram_gb": round(mem.available / (1024**3), 2),
            "ram_percent_used": mem.percent,
            "total_disk_gb": round(disk.total / (1024**3), 2),
            "free_disk_gb": round(disk.free / (1024**3), 2),
            "disk_percent_used": disk.percent,
        }
