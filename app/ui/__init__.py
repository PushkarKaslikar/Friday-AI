"""Presentation Layer for PySide6 Desktop User Interface."""

import sys

try:
    from PySide6.QtWidgets import QApplication

    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False

from app.logging import logger


class UIInitializer:
    """Manages PySide6 Qt Application instance creation and readiness validation."""

    def __init__(self) -> None:
        self._app: QApplication | None = None

    def initialize_qt_app(self) -> bool:
        """Verify PySide6 framework availability and initialize QApplication instance if needed.

        Returns:
            bool: True if Qt environment initialized successfully.
        """
        if not PYSIDE6_AVAILABLE:
            logger.error("PySide6 is not available in Python environment.")
            return False

        if QApplication.instance() is None:
            # Create headless/minimal instance for verification
            self._app = QApplication(sys.argv)
            self._app.setApplicationName("Friday AI Assistant")
            logger.info("QApplication instance successfully initialized.")
        else:
            self._app = QApplication.instance()
            logger.info("Existing QApplication instance attached.")

        return True


__all__ = ["PYSIDE6_AVAILABLE", "UIInitializer"]
