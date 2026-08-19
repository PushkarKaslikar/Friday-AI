"""Unit tests for ApplicationAdapter base abstraction, identity, states, and capabilities."""

from unittest.mock import MagicMock

from app.automation.apps.base import ApplicationAdapter
from app.automation.apps.models import (
    ApplicationCapability,
    ApplicationIdentity,
    ApplicationState,
)


class DummyAdapter(ApplicationAdapter):
    def __init__(self):
        self._identity = ApplicationIdentity(
            app_id="dummy",
            display_name="Dummy App",
            executable_names=["dummy.exe"],
            aliases=["dummy"],
            capabilities={ApplicationCapability.LAUNCH, ApplicationCapability.ATTACH},
        )
        self._state = ApplicationState.INSTALLED

    @property
    def identity(self) -> ApplicationIdentity:
        return self._identity

    @property
    def state(self) -> ApplicationState:
        return self._state

    def is_installed(self) -> bool:
        return True

    def is_running(self) -> bool:
        return False

    def find_windows(self):
        return []

    def attach(self, hwnd=None):
        return MagicMock()

    def launch(self, request=None):
        return MagicMock()

    def get_active_window(self):
        return None

    def health_check(self):
        return {"status": "HEALTHY"}


def test_application_adapter_properties():
    adapter = DummyAdapter()
    assert adapter.identity.app_id == "dummy"
    assert adapter.state == ApplicationState.INSTALLED
    assert ApplicationCapability.LAUNCH in adapter.capabilities
    assert adapter.is_installed() is True
    assert adapter.is_running() is False
