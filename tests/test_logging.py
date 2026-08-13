"""Unit tests for LoggingManager subsystem."""

from app.config.models import LoggingSettings
from app.logging import LoggingManager


def test_logging_initialization():
    settings = LoggingSettings(level="INFO", log_to_console=True, log_to_file=False)
    logging_manager = LoggingManager(settings=settings)
    assert logging_manager.is_initialized is False

    logging_manager.setup_logging()
    assert logging_manager.is_initialized is True


def test_logging_lifecycle_logs():
    settings = LoggingSettings(level="DEBUG", log_to_console=False, log_to_file=False)
    logging_manager = LoggingManager(settings=settings)
    logging_manager.setup_logging()

    logging_manager.log_startup("TestApp", "1.0.0", "test")
    logging_manager.log_shutdown("TestApp")
