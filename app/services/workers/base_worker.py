"""Reusable BaseWorker for non-blocking background task execution with progress and cancellation."""

import threading
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Generic, TypeVar

from app.logging import logger

T = TypeVar("T")


class BaseWorker(ABC, Generic[T]):
    """Abstract base class for asynchronous background worker tasks."""

    def __init__(
        self,
        worker_id: str,
        on_progress: Callable[[int, str], None] | None = None,
        on_success: Callable[[T], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self.worker_id = worker_id
        self.on_progress_cb = on_progress
        self.on_success_cb = on_success
        self.on_error_cb = on_error

        self._cancellation_event = threading.Event()
        self._is_running = False

    @property
    def is_cancelled(self) -> bool:
        """Check if worker cancellation has been requested."""
        return self._cancellation_event.is_set()

    @property
    def is_running(self) -> bool:
        """Check if worker is currently executing."""
        return self._is_running

    def request_cancellation(self) -> None:
        """Request cooperative cancellation of worker task."""
        self._cancellation_event.set()
        logger.info(f"Worker '{self.worker_id}': Cancellation requested.")

    def report_progress(self, percentage: int, message: str) -> None:
        """Emit progress update to registered callback."""
        if self.on_progress_cb:
            try:
                self.on_progress_cb(percentage, message)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"Worker '{self.worker_id}': Error in progress callback: {exc}"
                )

    @abstractmethod
    def run(self) -> T:
        """Execute background worker work payload. Implemented by concrete workers."""

    def execute(self) -> T | None:
        """Execute worker task wrapper managing state, progress, and error handling."""
        self._is_running = True
        logger.debug(f"Worker '{self.worker_id}': Started execution.")
        try:
            result = self.run()
            if not self.is_cancelled and self.on_success_cb:
                self.on_success_cb(result)
            return result
        except Exception as exc:
            logger.error(
                f"Worker '{self.worker_id}': Execution failed with error: {exc}"
            )
            if self.on_error_cb:
                self.on_error_cb(exc)
            raise
        finally:
            self._is_running = False
            logger.debug(f"Worker '{self.worker_id}': Execution completed.")
