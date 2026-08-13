"""Unit tests for constants module."""

from app.constants import (
    APP_NAME,
    APP_VERSION,
    MIN_PYTHON_VERSION,
    PROJECT_ROOT,
    REQUIRED_DIRECTORIES,
)


def test_app_constants():
    assert APP_NAME == "Friday AI Assistant"
    assert APP_VERSION == "1.0.0"
    assert MIN_PYTHON_VERSION == (3, 12)


def test_path_constants():
    assert PROJECT_ROOT.exists()
    assert len(REQUIRED_DIRECTORIES) > 0
