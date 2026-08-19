"""Unit tests for ApplicationAdapterRegistry deterministic resolution."""

import pytest

from app.automation.apps.base import ApplicationAdapter
from app.automation.apps.models import ApplicationIdentity, ApplicationState
from app.automation.apps.registry import ApplicationAdapterRegistry


class SampleAdapter(ApplicationAdapter):
    def __init__(self, app_id: str, aliases: list[str]):
        self._identity = ApplicationIdentity(
            app_id=app_id,
            display_name=app_id.capitalize(),
            executable_names=[f"{app_id}.exe"],
            aliases=aliases,
        )

    @property
    def identity(self) -> ApplicationIdentity:
        return self._identity

    @property
    def state(self) -> ApplicationState:
        return ApplicationState.INSTALLED

    def is_installed(self) -> bool:
        return True

    def is_running(self) -> bool:
        return False

    def find_windows(self):
        return []

    def attach(self, hwnd=None):
        return None

    def launch(self, request=None):
        return None

    def get_active_window(self):
        return None

    def health_check(self):
        return {}


def test_registry_resolution():
    registry = ApplicationAdapterRegistry()
    adapter1 = SampleAdapter("explorer", ["file explorer", "windows explorer"])
    registry.register_adapter(adapter1)

    assert registry.get_adapter("explorer") == adapter1
    assert registry.get_adapter("File Explorer") == adapter1
    assert registry.get_adapter("windows explorer") == adapter1
    assert registry.get_adapter("unknown") is None


def test_duplicate_registration_raises():
    registry = ApplicationAdapterRegistry()
    adapter1 = SampleAdapter("cmd", ["command prompt"])
    adapter2 = SampleAdapter("cmd", ["cmd2"])

    registry.register_adapter(adapter1)
    with pytest.raises(ValueError, match="already registered"):
        registry.register_adapter(adapter2)
