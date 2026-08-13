"""Unit tests for BaseService abstract base class and ServiceState."""

import pytest

from app.services.base.service_interface import BaseService, ServiceState


class DummyService(BaseService):
    """Concrete service for testing."""

    def __init__(
        self,
        name: str = "DummyService",
        is_critical: bool = False,
        fail_on_start: bool = False,
    ):
        super().__init__(name=name, is_critical=is_critical)
        self.fail_on_start = fail_on_start
        self.initialized = False
        self.started = False
        self.stopped = False

    def _do_initialize(self) -> None:
        self.initialized = True

    def _do_start(self) -> None:
        if self.fail_on_start:
            raise RuntimeError("Simulated startup failure")
        self.started = True

    def _do_stop(self) -> None:
        self.stopped = True


def test_base_service_lifecycle():
    service = DummyService()
    assert service.state == ServiceState.UNINITIALIZED
    assert service.uptime_seconds == 0.0

    service.initialize()
    assert service.state == ServiceState.INITIALIZED
    assert service.initialized is True

    service.start()
    assert service.state == ServiceState.RUNNING
    assert service.started is True
    assert service.uptime_seconds >= 0.0

    service.stop()
    assert service.state == ServiceState.STOPPED
    assert service.stopped is True


def test_base_service_failure():
    service = DummyService(fail_on_start=True)
    with pytest.raises(RuntimeError):
        service.start()

    assert service.state == ServiceState.FAILED
    assert service.failure_count == 1
    assert "Simulated startup failure" in service.last_error
