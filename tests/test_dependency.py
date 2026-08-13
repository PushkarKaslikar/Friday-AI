"""Unit tests for ApplicationContainer dependency injection container."""

from app.config.manager import ConfigurationManager
from app.dependency.container import ApplicationContainer
from app.logging import LoggingManager


def test_container_providers(app_container: ApplicationContainer):
    cm = app_container.config_manager()
    assert isinstance(cm, ConfigurationManager)

    lm = app_container.logging_manager()
    assert isinstance(lm, LoggingManager)
