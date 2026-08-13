"""Custom Header Bar for window controls, theme toggle, and settings."""

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager


class HeaderBar(QFrame):
    """Modern header bar with title, theme toggle, settings icon, and window buttons."""

    minimize_clicked = Signal()
    maximize_clicked = Signal()
    close_clicked = Signal()
    settings_clicked = Signal()

    def __init__(
        self,
        title: str = "Friday AI Assistant",
        theme_manager: ThemeManager | None = None,
        asset_manager: AssetManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title_text = title
        self.theme_manager = theme_manager or ThemeManager()
        self.asset_manager = asset_manager or AssetManager()
        self._drag_pos: QPoint | None = None

        self.setFixedHeight(40)
        self._setup_ui()
        self.theme_manager.theme_changed.connect(lambda _: self._update_styles())

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # Title Label
        self.title_label = QLabel(self.title_text, self)
        layout.addWidget(self.title_label)
        layout.addStretch()

        # Theme Toggle Button
        self.theme_btn = QPushButton(self)
        self.theme_btn.setFixedSize(28, 28)
        self.theme_btn.setToolTip("Toggle Dark/Light Theme")
        self.theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.theme_btn.clicked.connect(self._on_theme_toggle)
        layout.addWidget(self.theme_btn)

        # Settings Button
        self.settings_btn = QPushButton(self)
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(lambda: self.settings_clicked.emit())
        layout.addWidget(self.settings_btn)

        # Window Controls: Minimize, Close
        self.min_btn = QPushButton(self)
        self.min_btn.setFixedSize(28, 28)
        self.min_btn.setToolTip("Minimize to System Tray")
        self.min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.min_btn.clicked.connect(lambda: self.minimize_clicked.emit())
        layout.addWidget(self.min_btn)

        self.close_btn = QPushButton(self)
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setToolTip("Minimize to Tray")
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(lambda: self.close_clicked.emit())
        layout.addWidget(self.close_btn)

        self._update_styles()

    def _on_theme_toggle(self) -> None:
        self.theme_manager.toggle_theme()

    def _update_styles(self) -> None:
        p = self.theme_manager.palette
        self.setStyleSheet(f"""
            HeaderBar {{
                background-color: {p.bg_secondary};
                border-bottom: 1px solid {p.border};
            }}
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {p.bg_hover};
            }}
        """)
        self.title_label.setStyleSheet(
            f"color: {p.text_secondary}; font-weight: 600; font-size: 12px;"
        )

        theme_pixmap = self.asset_manager.get_pixmap(
            "theme", color=p.text_secondary, size=16
        )
        self.theme_btn.setIcon(theme_pixmap)

        settings_pixmap = self.asset_manager.get_pixmap(
            "settings", color=p.text_secondary, size=16
        )
        self.settings_btn.setIcon(settings_pixmap)

        min_pixmap = self.asset_manager.get_pixmap(
            "minimize", color=p.text_secondary, size=16
        )
        self.min_btn.setIcon(min_pixmap)

        close_pixmap = self.asset_manager.get_pixmap(
            "close", color=p.text_secondary, size=16
        )
        self.close_btn.setIcon(close_pixmap)
