"""Pytest test fixtures for unit tests."""

import sys
from collections.abc import Generator
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.dependency.container import ApplicationContainer


@pytest.fixture(scope="session")
def qapp():
    """Session-wide QApplication instance fixture."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Fixture providing temporary configuration directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


@pytest.fixture
def sample_json_config(temp_config_dir: Path) -> Path:
    """Fixture creating a valid sample settings.json file."""
    config_file = temp_config_dir / "settings.json"
    content = """{
        "app": {
            "name": "Test Friday AI",
            "version": "1.0.0-test",
            "environment": "development",
            "debug": true
        },
        "ui": {
            "theme": "dark",
            "start_minimized": false,
            "auto_start": false
        },
        "logging": {
            "level": "DEBUG",
            "log_to_console": false,
            "log_to_file": true,
            "max_file_size_mb": 5,
            "retention_days": 7
        }
    }"""
    config_file.write_text(content, encoding="utf-8")
    return config_file


@pytest.fixture
def config_manager(sample_json_config: Path) -> ConfigurationManager:
    """Fixture providing initialized ConfigurationManager."""
    return ConfigurationManager(json_path=sample_json_config)


@pytest.fixture
def app_container() -> ApplicationContainer:
    """Fixture providing clean ApplicationContainer."""
    container = ApplicationContainer()
    container.reset_singletons()
    yield container
    container.reset_singletons()


@pytest.fixture
def bootstrapper() -> Generator[AppBootstrapper, None, None]:
    """Fixture providing clean AppBootstrapper instance with automatic teardown."""
    b = AppBootstrapper()
    yield b
    if b.service_manager:
        b.service_manager.stop_all()


@pytest.fixture(autouse=True)
def clean_event_bus_and_singletons():
    """Autouse fixture ensuring clean EventBus and ServiceManager state for every test."""
    from app.services.core.service_manager import ServiceManager
    from app.services.events.event_bus import EventBus

    EventBus().clear()
    ServiceManager().clear()
    yield
    EventBus().clear()
    ServiceManager().clear()
