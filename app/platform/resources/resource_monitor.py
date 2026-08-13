"""Resource Monitor service tracking RAM, CPU, handles, descriptors, and idle state."""

import os
import time
from typing import Any

import psutil

from app.logging import logger
from app.services.base.service_interface import BaseService


class ResourceMonitor(BaseService):
    """Background service monitoring system resources, handle counts, and idle CPU detection."""

    def __init__(self, idle_cpu_threshold: float = 5.0) -> None:
        super().__init__(name="ResourceMonitor", is_critical=False)
        self.idle_cpu_threshold = idle_cpu_threshold
        self._process: psutil.Process | None = None
        self._start_time: float = time.time()

    def _do_initialize(self) -> None:
        """Initialize psutil process handle."""
        self._process = psutil.Process(os.getpid())
        logger.info("ResourceMonitor initialized.")

    def _do_start(self) -> None:
        """Start resource monitor."""
        logger.info("ResourceMonitor started.")

    def _do_stop(self) -> None:
        """Stop resource monitor."""
        logger.info("ResourceMonitor stopped.")

    def is_idle(self) -> bool:
        """Check if process CPU usage is below idle threshold."""
        if not self._process:
            return True
        try:
            return self._process.cpu_percent(interval=0.1) < self.idle_cpu_threshold
        except Exception:  # noqa: BLE001
            return True

    def get_resource_snapshot(self) -> dict[str, Any]:
        """Collect current resource usage metrics.

        Returns:
            dict: Snapshot of RAM, CPU, handles, open files, and idle status.
        """
        if not self._process:
            self._process = psutil.Process(os.getpid())

        try:
            mem = self._process.memory_info()
            handles = getattr(self._process, "num_handles", lambda: 0)()
            open_files = len(self._process.open_files())

            return {
                "rss_mb": round(mem.rss / (1024 * 1024), 2),
                "vms_mb": round(mem.vms / (1024 * 1024), 2),
                "cpu_percent": self._process.cpu_percent(interval=0.1),
                "num_threads": self._process.num_threads(),
                "num_handles": handles,
                "num_open_files": open_files,
                "is_idle": self.is_idle(),
                "uptime_seconds": round(time.time() - self._start_time, 2),
            }
        except Exception as exc:  # noqa: BLE001
            logger.error(f"ResourceMonitor: Error querying resource metrics: {exc}")
            return {"error": str(exc)}

    def health_check(self) -> dict[str, Any]:
        """Diagnostic health check payload."""
        data = super().health_check()
        data.update(self.get_resource_snapshot())
        return data
