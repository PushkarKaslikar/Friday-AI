"""Unit tests for HealthMonitor."""

from app.services.health.health_monitor import HealthMonitor
from tests.test_services_base import DummyService


def test_health_monitor_snapshot():
    hm = HealthMonitor()
    hm.initialize()
    hm.start()

    service = DummyService(name="MonitoredService")
    service.initialize()
    service.start()

    hm.register_service(service)
    snapshot = hm.run_health_check()

    assert snapshot["healthy"] is True
    assert snapshot["total_services"] == 1
    assert snapshot["services"][0]["name"] == "MonitoredService"

    hm.stop()
