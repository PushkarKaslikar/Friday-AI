"""Unit tests for VirtualDesktopManager queries and unsupported API fallback."""

from app.automation.desktop.models import VirtualDesktopInfo
from app.automation.desktop.virtual_desktop import VirtualDesktopManager


def test_get_virtual_desktop_info():
    vdesktop_mgr = VirtualDesktopManager()
    info = vdesktop_mgr.get_virtual_desktop_info()

    assert isinstance(info, VirtualDesktopInfo)
    assert info.total_desktops >= 1
