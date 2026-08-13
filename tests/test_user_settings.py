"""Unit tests for UserSettingsManager."""

from pathlib import Path

from app.services.events.event_bus import EventBus
from app.settings.user_settings_manager import UserSettingsManager


def test_user_settings_manager(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    event_bus = EventBus()
    usm = UserSettingsManager(settings_file=settings_file, event_bus=event_bus)

    # Test reading default value
    theme = usm.get("appearance", "theme")
    assert theme == "dark"

    # Test setting value
    usm.set("appearance", "theme", "light", auto_save=True)
    assert usm.get("appearance", "theme") == "light"

    # Reload from disk
    usm.load_settings()
    assert usm.get("appearance", "theme") == "light"
