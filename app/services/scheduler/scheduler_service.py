"""Background Scheduler Service foundation using APScheduler."""

from collections.abc import Callable
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.logging import logger
from app.services.base.service_interface import BaseService


class SchedulerService(BaseService):
    """Core Scheduler Service foundation providing background job scheduling triggers."""

    def __init__(self) -> None:
        super().__init__(name="SchedulerService", is_critical=False)
        self._scheduler: BackgroundScheduler | None = None

    def _do_initialize(self) -> None:
        """Initialize APScheduler BackgroundScheduler instance."""
        self._scheduler = BackgroundScheduler(daemon=True)
        logger.info("SchedulerService initialized.")

    def _do_start(self) -> None:
        """Start background scheduler loop."""
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
            logger.info("SchedulerService started.")

    def _do_stop(self) -> None:
        """Stop background scheduler loop."""
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=False)
            logger.info("SchedulerService stopped.")

    def add_interval_job(
        self,
        job_id: str,
        func: Callable[..., Any],
        seconds: int,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> bool:
        """Add an interval recurring scheduled job.

        Args:
            job_id: Unique string identifier for the job.
            func: Function to execute.
            seconds: Recurring interval in seconds.
            args: Positional function arguments.
            kwargs: Keyword function arguments.

        Returns:
            bool: True if job was registered successfully.
        """
        if not self._scheduler or not self._scheduler.running:
            logger.warning(
                f"SchedulerService: Cannot add job '{job_id}' when scheduler is not running."
            )
            return False

        try:
            self._scheduler.add_job(
                func=func,
                trigger=IntervalTrigger(seconds=seconds),
                id=job_id,
                args=args or [],
                kwargs=kwargs or {},
                replace_existing=True,
            )
            logger.info(
                f"SchedulerService: Added interval job '{job_id}' (every {seconds}s)."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"SchedulerService: Failed to add interval job '{job_id}': {exc}"
            )
            return False

    def remove_job(self, job_id: str) -> bool:
        """Remove a registered job by ID."""
        if not self._scheduler:
            return False
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"SchedulerService: Removed job '{job_id}'.")
            return True
        except Exception:  # noqa: BLE001
            return False

    def health_check(self) -> dict[str, Any]:
        """Collect diagnostic health info."""
        data = super().health_check()
        data["running"] = self._scheduler.running if self._scheduler else False
        data["job_count"] = (
            len(self._scheduler.get_jobs())
            if self._scheduler and self._scheduler.running
            else 0
        )
        return data
