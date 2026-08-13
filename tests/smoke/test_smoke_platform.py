"""Smoke test verifying Windows platform integration components."""

from app.platform.identity.app_identity import APP_IDENTITY
from app.platform.info.system_info import SystemInfo
from app.platform.notifications.notification_manager import NotificationManager
from app.platform.process.process_manager import ProcessManager
from app.platform.registry.registry_manager import RegistryManager
from app.platform.resources.resource_monitor import ResourceMonitor
from app.platform.startup.startup_manager import StartupManager
from app.platform.version.version_manager import VersionManager


def test_smoke_platform_components():
    reg = RegistryManager()
    assert reg is not None

    startup = StartupManager(registry_manager=reg)
    assert startup.get_executable_command() != ""

    notifier = NotificationManager()
    notifier.clear_history()
    notifier.show_info("Smoke Test", "Notification Test")
    assert len(notifier.get_history()) == 1

    assert APP_IDENTITY.name == "Friday AI Assistant"

    vm = VersionManager()
    info = vm.get_build_info()
    assert info["version"] == APP_IDENTITY.version

    sys_info = SystemInfo().get_system_summary()
    assert sys_info["os_name"] == "Windows"

    pm = ProcessManager()
    health = pm.get_process_health()
    assert health["pid"] > 0

    rm = ResourceMonitor()
    rm.initialize()
    rm.start()
    snapshot = rm.get_resource_snapshot()
    assert "rss_mb" in snapshot
    rm.stop()
