"""Centralized Service Manager for registering, managing, starting, and stopping background services."""

import threading
from typing import Any, Optional

from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.services.events.event_models import (
    ServiceFailed,
    ServiceStarted,
    ServiceStopped,
)


class ServiceManager:
    """Centralized manager and orchestrator for all background system services."""

    _instance: Optional["ServiceManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, event_bus: EventBus | None = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.event_bus = event_bus or EventBus()
        self._lock = threading.RLock()
        self._services: dict[str, BaseService] = {}
        self._initialized = True
        logger.info("ServiceManager initialized.")

    def register_service(self, service: BaseService) -> None:
        """Register a service instance with the ServiceManager.

        Args:
            service: BaseService instance.
        """
        with self._lock:
            if service.name in self._services:
                logger.warning(
                    f"ServiceManager: Service '{service.name}' is already registered."
                )
                return

            self._services[service.name] = service
            logger.info(
                f"ServiceManager: Registered service '{service.name}' (critical={service.is_critical})."
            )

    def get_service(self, name: str) -> BaseService | None:
        """Retrieve registered service by name."""
        with self._lock:
            return self._services.get(name)

    def initialize_all(self) -> None:
        """Initialize all registered services."""
        with self._lock:
            logger.info(
                f"ServiceManager: Initializing {len(self._services)} registered services..."
            )
            for service in self._services.values():
                try:
                    service.initialize()
                    logger.info(
                        f"ServiceManager: Service '{service.name}' initialized."
                    )
                except Exception as exc:
                    logger.error(
                        f"ServiceManager: Failed to initialize service '{service.name}': {exc}"
                    )
                    self.event_bus.publish(
                        ServiceFailed(service_name=service.name, error_message=str(exc))
                    )
                    if service.is_critical:
                        raise

    def start_all(self) -> None:
        """Start all registered services."""
        with self._lock:
            logger.info(
                f"ServiceManager: Starting {len(self._services)} registered services..."
            )
            for service in self._services.values():
                try:
                    service.start()
                    logger.info(f"ServiceManager: Service '{service.name}' started.")
                    self.event_bus.publish(ServiceStarted(service_name=service.name))
                except Exception as exc:
                    logger.error(
                        f"ServiceManager: Failed to start service '{service.name}': {exc}"
                    )
                    self.event_bus.publish(
                        ServiceFailed(service_name=service.name, error_message=str(exc))
                    )
                    if service.is_critical:
                        raise

    def stop_all(self) -> None:
        """Stop all registered services in reverse registration order."""
        with self._lock:
            services_list = list(self._services.values())
            logger.info(
                f"ServiceManager: Stopping {len(services_list)} registered services..."
            )
            for service in reversed(services_list):
                try:
                    service.stop()
                    logger.info(f"ServiceManager: Service '{service.name}' stopped.")
                    self.event_bus.publish(ServiceStopped(service_name=service.name))
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        f"ServiceManager: Exception while stopping service '{service.name}': {exc}"
                    )

    def shutdown_all(self) -> None:
        """Perform full shutdown and cleanup across all registered services."""
        with self._lock:
            services_list = list(self._services.values())
            logger.info(
                f"ServiceManager: Shutting down {len(services_list)} registered services..."
            )
            for service in reversed(services_list):
                try:
                    service.shutdown()
                    logger.info(
                        f"ServiceManager: Service '{service.name}' shutdown complete."
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        f"ServiceManager: Error shutting down service '{service.name}': {exc}"
                    )

    def restart_service(self, name: str) -> bool:
        """Restart a specific registered service by name."""
        with self._lock:
            service = self.get_service(name)
            if not service:
                logger.warning(
                    f"ServiceManager: Cannot restart unregistered service '{name}'."
                )
                return False

            try:
                service.restart()
                logger.info(f"ServiceManager: Service '{name}' restarted.")
                return True
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    f"ServiceManager: Failed to restart service '{name}': {exc}"
                )
                self.event_bus.publish(
                    ServiceFailed(service_name=name, error_message=str(exc))
                )
                return False

    def get_status_summary(self) -> dict[str, Any]:
        """Get summary report of all service states."""
        with self._lock:
            return {
                name: {
                    "state": s.state.name,
                    "is_critical": s.is_critical,
                    "uptime": s.uptime_seconds,
                    "failures": s.failure_count,
                }
                for name, s in self._services.items()
            }
