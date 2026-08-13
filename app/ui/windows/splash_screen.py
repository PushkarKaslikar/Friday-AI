"""Splash Screen window displayed during application initialization."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSplashScreen,
    QVBoxLayout,
)

from app.constants.application import APP_NAME, APP_VERSION
from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager


class SplashScreen(QSplashScreen):
    """Frameless custom splash screen with application branding, progress bar, and status labels."""

    def __init__(
        self,
        theme_manager: ThemeManager | None = None,
        asset_manager: AssetManager | None = None,
    ) -> None:
        self.theme_manager = theme_manager or ThemeManager()
        self.asset_manager = asset_manager or AssetManager()

        # Build Container Canvas Widget
        self.container = QFrame()
        self.container.setFixedSize(480, 280)
        self.container.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )

        super().__init__(self.container.grab())
        self._setup_ui()
        self.center_on_screen()

    def _setup_ui(self) -> None:
        p = self.theme_manager.palette

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(32, 32, 32, 28)
        main_layout.setSpacing(16)

        # Branding Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(16)

        logo_pixmap = self.asset_manager.get_pixmap("app_logo", color=p.accent, size=48)
        self.logo_label = QLabel(self.container)
        self.logo_label.setPixmap(logo_pixmap)
        header_layout.addWidget(self.logo_label)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)

        self.title_label = QLabel(APP_NAME, self.container)
        self.title_label.setStyleSheet(
            f"color: {p.text_primary}; font-size: 22px; font-weight: 700; letter-spacing: 1px;"
        )

        self.subtitle_label = QLabel(
            f"Personal Desktop AI Assistant • v{APP_VERSION}", self.container
        )
        self.subtitle_label.setStyleSheet(
            f"color: {p.text_secondary}; font-size: 12px;"
        )

        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)
        main_layout.addStretch()

        # Progress Bar & Status Text
        self.status_label = QLabel(
            "Initializing application foundation...", self.container
        )
        self.status_label.setStyleSheet(f"color: {p.text_muted}; font-size: 11px;")
        main_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar(self.container)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {p.bg_secondary};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {p.accent};
                border-radius: 3px;
            }}
        """)
        main_layout.addWidget(self.progress_bar)

        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {p.bg_card};
                border: 1px solid {p.border};
                border-radius: 12px;
            }}
        """)

    def update_progress(self, percentage: int, message: str) -> None:
        """Update splash screen progress bar value and status text.

        Args:
            percentage: Integer percentage (0 to 100).
            message: Status message text.
        """
        self.progress_bar.setValue(percentage)
        self.status_label.setText(message)
        self.repaint()

    def center_on_screen(self) -> None:
        """Center splash screen on primary screen."""
        if screen := self.screen():
            geometry = screen.geometry()
            x = (geometry.width() - self.container.width()) // 2
            y = (geometry.height() - self.container.height()) // 2
            self.container.move(x, y)
