"""Unit tests for configuration manager and settings models."""

from pathlib import Path

import pytest

from app.config.manager import ConfigurationManager
from app.config.models import Settings
from app.exceptions.config import ConfigurationError


def test_load_valid_settings(config_manager: ConfigurationManager):
    settings = config_manager.load_settings()
    assert isinstance(settings, Settings)
    assert settings.app.name == "Test Friday AI"
    assert settings.app.environment == "development"
    assert settings.logging.level == "DEBUG"


def test_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("FRIDAY_APP_NAME", "Env Override Assistant")
    monkeypatch.setenv("FRIDAY_LOG_LEVEL", "WARNING")

    cm = ConfigurationManager(json_path=tmp_path / "non_existent.json")
    settings = cm.load_settings()

    assert settings.app.name == "Env Override Assistant"
    assert settings.logging.level == "WARNING"


def test_invalid_json_config(tmp_path: Path):
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{bad json}", encoding="utf-8")
    cm = ConfigurationManager(json_path=invalid_file)
    with pytest.raises(ConfigurationError):
        cm.load_settings()
