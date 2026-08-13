"""Performance Monitoring Service tracking RAM, CPU, thread utilization, and metrics using psutil."""

import os
import time
from typing import Any

import psutil

from app.logging import logger
from app.services.base.service_interface import BaseService


class PerformanceMonitor(BaseService):
    """Monitors system resources (RAM, CPU, thread count, execution metrics) via psutil."""

    def __init__(self, interval_sec: int = 15) -> None:
        super().__init__(name="PerformanceMonitor", is_critical=False)
        self.interval_sec = interval_sec
        self._process: psutil.Process | None = None
        self._start_time: float = time.time()

    def _do_initialize(self) -> None:
        """Initialize psutil process handle."""
        self._process = psutil.Process(os.getpid())
        logger.info("PerformanceMonitor initialized.")

    def _do_start(self) -> None:
        """Start performance monitor."""
        logger.info("PerformanceMonitor started.")

    def _do_stop(self) -> None:
        """Stop performance monitor."""
        logger.info("PerformanceMonitor stopped.")

    def get_metrics(self) -> dict[str, Any]:
        """Collect current process performance metrics snapshot.

        Returns:
            dict: Metrics dictionary containing RAM (MB), CPU (%), thread count, and uptime.
        """
        if not self._process:
            self._process = psutil.Process(os.getpid())

        try:
            mem_info = self._process.memory_info()
            cpu_percent = self._process.cpu_percent(interval=0.1)
            num_threads = self._process.num_threads()
            uptime_sec = round(time.time() - self._start_time, 2)

            metrics = {
                "ram_usage_mb": round(mem_info.rss / (1024 * 1024), 2),
                "ram_virtual_mb": round(mem_info.vms / (1024 * 1024), 2),
                "cpu_percent": cpu_percent,
                "thread_count": num_threads,
                "uptime_seconds": uptime_sec,
                "system_cpu_percent": psutil.cpu_percent(),
                "system_ram_percent": psutil.virtual_memory().percent,
            }
            logger.debug(
                f"Performance Metrics: RAM={metrics['ram_usage_mb']}MB, CPU={metrics['cpu_percent']}%, Threads={num_threads}"
            )
            return metrics
        except Exception as exc:  # noqa: BLE001
            logger.error(f"PerformanceMonitor: Error querying metrics: {exc}")
            return {
                "ram_usage_mb": 0.0,
                "cpu_percent": 0.0,
                "thread_count": 0,
                "uptime_seconds": 0.0,
                "error": str(exc),
            }

    def health_check(self) -> dict[str, Any]:
        """Diagnostic health check payload."""
        data = super().health_check()
        data.update(self.get_metrics())
        return data
