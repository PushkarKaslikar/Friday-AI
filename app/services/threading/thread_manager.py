"""Centralized Thread Manager controlling thread pool execution and worker tracking."""

import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional, TypeVar

from app.logging import logger

T = TypeVar("T")


class ThreadManager:
    """Manages thread pools, worker thread creation, utilization tracking, and thread safety."""

    _instance: Optional["ThreadManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_workers: int = 8) -> None:
        if getattr(self, "_initialized", False):
            return

        self._max_workers = max_workers
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="FridayWorker",
        )
        self._lock = threading.RLock()
        self._active_tasks: dict[str, Future] = {}
        self._initialized = True
        logger.info(f"ThreadManager initialized with max_workers={max_workers}.")

    @property
    def active_task_count(self) -> int:
        """Count of currently active submitted tasks."""
        with self._lock:
            return len(self._active_tasks)

    def submit_task(
        self,
        task_id: str,
        fn: Callable[..., T],
        *args,
        callback: Callable[[T], None] | None = None,
        error_callback: Callable[[Exception], None] | None = None,
        **kwargs,
    ) -> Future[T]:
        """Submit callable function to background thread pool.

        Args:
            task_id: Unique descriptor ID for active task tracking.
            fn: Function to execute in background thread.
            callback: Optional completion callback receiving function return result.
            error_callback: Optional error callback receiving exception if raised.

        Returns:
            Future: Concurrent future object representing pending result.
        """

        def wrapped_task() -> T:
            try:
                result = fn(*args, **kwargs)
                if callback:
                    try:
                        callback(result)
                    except Exception as cb_exc:  # noqa: BLE001
                        logger.error(
                            f"ThreadManager: Exception in completion callback for '{task_id}': {cb_exc}"
                        )
                return result
            except Exception as exc:
                logger.error(f"ThreadManager: Task '{task_id}' raised exception: {exc}")
                if error_callback:
                    try:
                        error_callback(exc)
                    except Exception as err_cb_exc:  # noqa: BLE001
                        logger.error(
                            f"ThreadManager: Exception in error callback for '{task_id}': {err_cb_exc}"
                        )
                raise
            finally:
                with self._lock:
                    self._active_tasks.pop(task_id, None)

        with self._lock:
            future = self._executor.submit(wrapped_task)
            self._active_tasks[task_id] = future
            logger.debug(f"ThreadManager: Task '{task_id}' submitted.")
            return future

    def cancel_task(self, task_id: str) -> bool:
        """Attempt to cancel pending task by ID."""
        with self._lock:
            future = self._active_tasks.get(task_id)
            if future:
                cancelled = future.cancel()
                if cancelled:
                    self._active_tasks.pop(task_id, None)
                    logger.info(f"ThreadManager: Task '{task_id}' cancelled.")
                return cancelled
        return False

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown thread pool executor cleanly."""
        with self._lock:
            logger.info("ThreadManager: Shutting down worker thread pool...")
            self._executor.shutdown(wait=wait, cancel_futures=True)
            self._active_tasks.clear()
            logger.info("ThreadManager: Worker thread pool shutdown complete.")
