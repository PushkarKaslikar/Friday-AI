"""Unit tests for MonitorManager multi-monitor topology discovery."""

from app.automation.desktop.models import MonitorInfo
from app.automation.desktop.monitor_manager import MonitorManager


def test_list_monitors_returns_valid_monitors():
    mgr = MonitorManager()
    monitors = mgr.list_monitors()

    assert len(monitors) >= 1
    primary = mgr.get_primary_monitor()
    assert primary is not None
    assert primary.is_primary is True
    assert primary.width > 0
    assert primary.height > 0


def test_get_monitor_for_point():
    mgr = MonitorManager()
    mon = mgr.get_monitor_for_point(10, 10)
    assert isinstance(mon, MonitorInfo)
    assert mon.width > 0
