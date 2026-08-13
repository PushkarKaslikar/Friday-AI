"""Process Manager managing main process, child subprocesses, and process health."""

import os
from typing import Any

import psutil

from app.logging import logger


class ProcessManager:
    """Manages application process instance, child process tracking, and resource limits."""

    def __init__(self) -> None:
        self._current_process = psutil.Process(os.getpid())

    def get_process_health(self) -> dict[str, Any]:
        """Collect current process health summary dictionary."""
        try:
            mem = self._current_process.memory_info()
            children = self._current_process.children(recursive=True)

            return {
                "pid": self._current_process.pid,
                "status": self._current_process.status(),
                "num_threads": self._current_process.num_threads(),
                "num_children": len(children),
                "rss_mb": round(mem.rss / (1024 * 1024), 2),
                "cpu_percent": self._current_process.cpu_percent(interval=0.1),
            }
        except Exception as exc:  # noqa: BLE001
            logger.error(f"ProcessManager: Error collecting health metrics: {exc}")
            return {"pid": os.getpid(), "error": str(exc)}

    def terminate_child_processes(self) -> int:
        """Terminate all child processes spawned by application."""
        count = 0
        try:
            children = self._current_process.children(recursive=True)
            for child in children:
                child.terminate()
                count += 1
            logger.info(f"ProcessManager: Terminated {count} child processes.")
        except Exception as exc:  # noqa: BLE001
            logger.error(f"ProcessManager: Error terminating child processes: {exc}")
        return count
