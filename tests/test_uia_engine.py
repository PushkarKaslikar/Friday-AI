"""Unit and integration tests for UIAutomationEngine."""

import sys

import pytest

from app.automation.errors import ElementNotFoundError
from app.automation.models import UIAStatus
from app.automation.uia.uia_engine import UIAutomationEngine


def test_uia_engine_availability():
    engine = UIAutomationEngine()
    if sys.platform == "win32":
        assert engine.is_available() is True
    else:
        assert engine.is_available() is False


def test_uia_engine_initialization():
    engine = UIAutomationEngine()
    init_success = engine.initialize()
    if sys.platform == "win32":
        assert init_success is True
        assert engine.metrics.engine_initializations == 1
    else:
        assert init_success is False


def test_uia_engine_health_status():
    engine = UIAutomationEngine()
    health = engine.get_health_status()

    assert "status" in health
    assert "platform" in health
    assert "pywinauto" in health
    assert "pywin32" in health
    assert "metrics" in health

    if sys.platform == "win32":
        assert health["status"] == UIAStatus.HEALTHY.value
        assert health["pywinauto"] == "AVAILABLE"
        assert health["pywin32"] == "AVAILABLE"


def test_uia_engine_get_root_element_invalid_hwnd():
    engine = UIAutomationEngine()
    if not engine.is_available():
        pytest.skip("UIA engine not available on host platform.")

    with pytest.raises(ElementNotFoundError):
        engine.get_root_element(-1)


def test_uia_engine_services_access():
    engine = UIAutomationEngine()
    assert engine.get_tree_walker() is not None
    assert engine.get_element_finder() is not None
