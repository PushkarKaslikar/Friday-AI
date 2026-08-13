"""Unit tests for environment validation and bootstrapping sequence."""

from app.bootstrap.bootstrapper import AppBootstrapper
from app.bootstrap.validator import EnvironmentValidator


def test_environment_validator():
    validator = EnvironmentValidator()
    result = validator.validate_all()
    assert result.is_valid is True
    assert len(result.errors) == 0


def test_app_bootstrapper_run(bootstrapper: AppBootstrapper):
    result = bootstrapper.run()
    assert result.success is True
    assert result.settings is not None
    assert result.logging_manager is not None
    assert result.container is not None
    assert result.qt_app is not None
    assert result.main_window is not None
    assert result.tray_manager is not None
