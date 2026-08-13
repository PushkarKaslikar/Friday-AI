"""Unit tests for ServiceManager."""

from app.services.core.service_manager import ServiceManager
from tests.test_services_base import DummyService


def test_service_manager_registration():
    sm = ServiceManager()
    service = DummyService(name="TestService1")

    sm.register_service(service)
    assert sm.get_service("TestService1") == service

    sm.initialize_all()
    sm.start_all()
    assert service.state.name == "RUNNING"

    summary = sm.get_status_summary()
    assert "TestService1" in summary

    sm.stop_all()
    assert service.state.name == "STOPPED"
