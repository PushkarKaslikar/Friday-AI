"""Reusable FridayCard container widget with modern styling."""

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager


class FridayCard(QFrame):
    """Modern card container with header icon, title, description, and status indicator."""

    def __init__(
        self,
        title: str,
        description: str,
        icon_name: str | None = None,
        theme_manager: ThemeManager | None = None,
        asset_manager: AssetManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title_text = title
        self.description_text = description
        self.icon_name = icon_name
        self.theme_manager = theme_manager or ThemeManager()
        self.asset_manager = asset_manager or AssetManager()

        self._setup_ui()
        self.theme_manager.theme_changed.connect(lambda _: self._update_card_styles())

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(10)

        # Header with icon and title
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        if self.icon_name:
            self.icon_label = QLabel(self)
            self.icon_label.setFixedSize(24, 24)
            header_layout.addWidget(self.icon_label)

        self.title_label = QLabel(self.title_text, self)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        main_layout.addLayout(header_layout)

        # Description text
        self.desc_label = QLabel(self.description_text, self)
        self.desc_label.setWordWrap(True)
        main_layout.addWidget(self.desc_label)

        self._update_card_styles()

    def _update_card_styles(self) -> None:
        p = self.theme_manager.palette
        self.setStyleSheet(f"""
            FridayCard {{
                background-color: {p.bg_card};
                border: 1px solid {p.border};
                border-radius: 8px;
            }}
            FridayCard:hover {{
                border: 1px solid {p.border_light};
                background-color: {p.bg_hover};
            }}
        """)
        self.title_label.setStyleSheet(
            f"color: {p.text_primary}; font-size: 15px; font-weight: 600;"
        )
        self.desc_label.setStyleSheet(
            f"color: {p.text_secondary}; font-size: 12px; line-height: 1.4;"
        )
        if self.icon_name and hasattr(self, "icon_label"):
            pixmap = self.asset_manager.get_pixmap(
                self.icon_name, color=p.accent, size=24
            )
            self.icon_label.setPixmap(pixmap)
