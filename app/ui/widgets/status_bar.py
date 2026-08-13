"""Application Status Bar Widget."""

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from app.constants.application import APP_VERSION
from app.ui.themes.theme_manager import ThemeManager


class FridayStatusBar(QFrame):
    """Custom status bar displaying live application state, version, and status dot."""

    def __init__(
        self,
        version: str = APP_VERSION,
        theme_manager: ThemeManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.version = version
        self.theme_manager = theme_manager or ThemeManager()

        self.setFixedHeight(28)
        self._setup_ui()
        self.theme_manager.theme_changed.connect(lambda _: self._update_styles())

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        # Status Indicator Dot
        self.status_dot = QLabel("●", self)
        self.status_label = QLabel("Friday Assistant Active in Background", self)

        layout.addWidget(self.status_dot)
        layout.addWidget(self.status_label)
        layout.addStretch()

        # Version Badge
        self.version_label = QLabel(f"v{self.version}", self)
        layout.addWidget(self.version_label)

        self._update_styles()

    def set_status_message(self, message: str, is_error: bool = False) -> None:
        """Update live status bar text and dot color."""
        self.status_label.setText(message)
        p = self.theme_manager.palette
        dot_color = p.status_error if is_error else p.status_success
        self.status_dot.setStyleSheet(f"color: {dot_color}; font-size: 10px;")

    def _update_styles(self) -> None:
        p = self.theme_manager.palette
        self.setStyleSheet(f"""
            FridayStatusBar {{
                background-color: {p.bg_secondary};
                border-top: 1px solid {p.border};
            }}
        """)
        self.status_dot.setStyleSheet(f"color: {p.status_success}; font-size: 10px;")
        self.status_label.setStyleSheet(f"color: {p.text_secondary}; font-size: 11px;")
        self.version_label.setStyleSheet(
            f"color: {p.text_muted}; font-size: 11px; padding: 2px 6px; background-color: {p.bg_card}; border-radius: 3px;"
        )
