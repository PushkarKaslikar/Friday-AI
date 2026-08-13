"""Settings Window providing multi-category settings framework."""

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager
from app.ui.widgets.card import FridayCard


class SettingsWindow(QDialog):
    """Settings Window dialog with category navigation sidebar and panel stack."""

    def __init__(
        self,
        theme_manager: ThemeManager | None = None,
        asset_manager: AssetManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.theme_manager = theme_manager or ThemeManager()
        self.asset_manager = asset_manager or AssetManager()

        self.setWindowTitle("Friday Assistant - Settings")
        self.resize(750, 500)
        self.setMinimumSize(640, 420)

        self._setup_ui()
        self.theme_manager.theme_changed.connect(lambda _: self._update_styles())

    def _setup_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Categories Sidebar List
        self.category_list = QListWidget(self)
        self.category_list.setFixedWidth(200)

        categories = [
            "General",
            "Appearance",
            "Audio & Voice",
            "AI Provider",
            "Plugins",
            "Privacy & Security",
            "Performance",
            "Advanced",
        ]

        for cat in categories:
            item = QListWidgetItem(cat)
            item.setSizeHint(item.sizeHint())
            self.category_list.addItem(item)

        main_layout.addWidget(self.category_list)

        # Content Panel Stack
        self.panel_stack = QStackedWidget(self)

        for cat in categories:
            panel = QWidget()
            panel_layout = QVBoxLayout(panel)
            panel_layout.setContentsMargins(24, 24, 24, 24)
            panel_layout.setSpacing(16)

            title_label = QLabel(f"{cat} Settings", panel)
            title_label.setObjectName("PanelTitle")

            card = FridayCard(
                title=f"{cat} Subsystem Configuration (Phase 1.2 Shell)",
                description=f"Settings options for {cat} will be populated as corresponding feature modules are introduced in future phases.",
                icon_name="settings",
            )

            panel_layout.addWidget(title_label)
            panel_layout.addWidget(card)
            panel_layout.addStretch()

            self.panel_stack.addWidget(panel)

        main_layout.addWidget(self.panel_stack)

        self.category_list.currentRowChanged.connect(self.panel_stack.setCurrentIndex)
        self.category_list.setCurrentRow(0)

        self._update_styles()

    def _update_styles(self) -> None:
        p = self.theme_manager.palette
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {p.bg_primary};
            }}
            QListWidget {{
                background-color: {p.bg_secondary};
                border: none;
                border-right: 1px solid {p.border};
                outline: none;
                padding-top: 8px;
            }}
            QListWidget::item {{
                height: 38px;
                padding-left: 16px;
                color: {p.text_secondary};
                border: none;
            }}
            QListWidget::item:hover {{
                background-color: {p.bg_hover};
                color: {p.text_primary};
            }}
            QListWidget::item:selected {{
                background-color: {p.accent_light};
                color: {p.accent};
                font-weight: 600;
                border-left: 3px solid {p.accent};
            }}
            QLabel#PanelTitle {{
                color: {p.text_primary};
                font-size: 20px;
                font-weight: 700;
            }}
        """)
