"""Health Monitoring Service collecting diagnostic snapshots across all application subsystems."""

from typing import Any

from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.services.events.event_models import HealthRecovered, HealthWarning
from app.services.threading.thread_manager import ThreadManager


class HealthMonitor(BaseService):
    """Monitors system health, service states, thread pool utilization, and issues health events."""

    def __init__(
        self,
        event_bus: EventBus | None = None,
        thread_manager: ThreadManager | None = None,
    ) -> None:
        super().__init__(name="HealthMonitor", is_critical=False)
        self.event_bus = event_bus or EventBus()
        self.thread_manager = thread_manager or ThreadManager()

        self._service_providers: list[BaseService] = []
        self._unhealthy_services: set[str] = set()

    def register_service(self, service: BaseService) -> None:
        """Register a service instance for health monitoring."""
        if service not in self._service_providers:
            self._service_providers.append(service)
            logger.debug(f"HealthMonitor: Registered service '{service.name}'.")

    def _do_initialize(self) -> None:
        """Initialize health monitor resources."""
        logger.info("HealthMonitor initialized.")

    def _do_start(self) -> None:
        """Start health monitor."""
        logger.info("HealthMonitor started.")

    def _do_stop(self) -> None:
        """Stop health monitor."""
        logger.info("HealthMonitor stopped.")

    def run_health_check(self) -> dict[str, Any]:
        """Perform system-wide health check snapshot across all registered services.

        Returns:
            dict: Summary diagnostic health report.
        """
        service_reports: list[dict[str, Any]] = []
        unhealthy_count = 0

        for service in self._service_providers:
            report = service.health_check()
            service_reports.append(report)

            state = report.get("state")
            name = service.name

            if state in ("FAILED", "STOPPED") and service.is_critical:
                unhealthy_count += 1
                if name not in self._unhealthy_services:
                    self._unhealthy_services.add(name)
                    msg = f"Critical service '{name}' is in {state} state!"
                    logger.warning(f"HealthMonitor: {msg}")
                    self.event_bus.publish(
                        HealthWarning(service_name=name, warning_message=msg)
                    )
            else:
                if name in self._unhealthy_services:
                    self._unhealthy_services.remove(name)
                    logger.info(f"HealthMonitor: Service '{name}' health recovered.")
                    self.event_bus.publish(HealthRecovered(service_name=name))

        active_threads = self.thread_manager.active_task_count

        return {
            "healthy": unhealthy_count == 0,
            "total_services": len(self._service_providers),
            "unhealthy_count": unhealthy_count,
            "active_worker_threads": active_threads,
            "services": service_reports,
        }
