"""Sidebar Navigation Widget providing tab switching interface."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui.navigation.navigation_manager import NavigationManager
from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager


class SidebarButton(QPushButton):
    """Custom sidebar navigation button with active state indicator styling."""

    def __init__(
        self,
        key: str,
        title: str,
        icon_name: str,
        asset_manager: AssetManager,
        theme_manager: ThemeManager,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.key = key
        self.title = title
        self.icon_name = icon_name
        self.asset_manager = asset_manager
        self.theme_manager = theme_manager
        self._is_active = False

        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._setup_ui()
        self.update_style()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(20, 20)

        self.text_label = QLabel(self.title, self)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()

    def set_active(self, active: bool) -> None:
        """Set active state and update styling."""
        self._is_active = active
        self.setChecked(active)
        self.update_style()

    def update_style(self) -> None:
        p = self.theme_manager.palette
        icon_color = p.accent if self._is_active else p.text_secondary
        text_color = p.text_primary if self._is_active else p.text_secondary
        bg_color = p.accent_light if self._is_active else "transparent"
        border_left = (
            f"3px solid {p.accent}" if self._is_active else "3px solid transparent"
        )

        pixmap = self.asset_manager.get_pixmap(
            self.icon_name, color=icon_color, size=20
        )
        self.icon_label.setPixmap(pixmap)

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: none;
                border-left: {border_left};
                border-radius: 6px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {p.bg_hover};
            }}
            QLabel {{
                color: {text_color};
                font-weight: {"600" if self._is_active else "400"};
                font-size: 13px;
                background: transparent;
            }}
        """)


class SidebarWidget(QFrame):
    """Sidebar navigation bar container widget."""

    settings_clicked = Signal()

    def __init__(
        self,
        navigation_manager: NavigationManager | None = None,
        theme_manager: ThemeManager | None = None,
        asset_manager: AssetManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.navigation_manager = navigation_manager or NavigationManager()
        self.theme_manager = theme_manager or ThemeManager()
        self.asset_manager = asset_manager or AssetManager()

        self.setFixedWidth(220)
        self._buttons: list[SidebarButton] = []

        self._setup_ui()
        self.navigation_manager.page_changed.connect(self._on_page_changed)
        self.theme_manager.theme_changed.connect(lambda _: self._update_theme_styles())

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 12, 8, 12)
        main_layout.setSpacing(4)

        # Application Logo / Header Branding
        brand_container = QWidget(self)
        brand_layout = QHBoxLayout(brand_container)
        brand_layout.setContentsMargins(12, 8, 12, 16)
        brand_layout.setSpacing(10)

        self.logo_label = QLabel(brand_container)
        self.logo_label.setFixedSize(28, 28)
        self._update_logo()

        brand_text_layout = QVBoxLayout()
        brand_text_layout.setSpacing(0)

        self.title_label = QLabel("FRIDAY", brand_container)
        self.subtitle_label = QLabel("AI Assistant", brand_container)

        brand_text_layout.addWidget(self.title_label)
        brand_text_layout.addWidget(self.subtitle_label)

        brand_layout.addWidget(self.logo_label)
        brand_layout.addLayout(brand_text_layout)
        brand_layout.addStretch()

        main_layout.addWidget(brand_container)

        # Navigation items
        nav_items = [
            ("home", "Home", "home"),
            ("assistant", "Assistant", "assistant"),
            ("memory", "Memory", "memory"),
            ("automation", "Automation", "automation"),
            ("plugins", "Plugins", "plugins"),
            ("logs", "Logs", "logs"),
            ("diagnostics", "Diagnostics", "diagnostics"),
        ]

        for index, (key, title, icon_name) in enumerate(nav_items):
            btn = SidebarButton(
                key=key,
                title=title,
                icon_name=icon_name,
                asset_manager=self.asset_manager,
                theme_manager=self.theme_manager,
                parent=self,
            )
            btn.clicked.connect(
                lambda checked, idx=index: self.navigation_manager.navigate_to_index(
                    idx
                )
            )
            self._buttons.append(btn)
            main_layout.addWidget(btn)

        main_layout.addStretch()

        # Settings button at bottom of sidebar
        self.settings_btn = SidebarButton(
            key="settings",
            title="Settings",
            icon_name="settings",
            asset_manager=self.asset_manager,
            theme_manager=self.theme_manager,
            parent=self,
        )
        self.settings_btn.clicked.connect(lambda: self.settings_clicked.emit())
        main_layout.addWidget(self.settings_btn)

        # Set initial active tab
        self._on_page_changed(
            self.navigation_manager.current_index, self.navigation_manager.current_key
        )
        self._update_theme_styles()

    def _update_logo(self) -> None:
        p = self.theme_manager.palette
        pixmap = self.asset_manager.get_pixmap("app_logo", color=p.accent, size=28)
        self.logo_label.setPixmap(pixmap)

    def _on_page_changed(self, index: int, key: str) -> None:
        for idx, btn in enumerate(self._buttons):
            btn.set_active(idx == index)

    def _update_theme_styles(self) -> None:
        p = self.theme_manager.palette
        self.setStyleSheet(f"""
            SidebarWidget {{
                background-color: {p.bg_secondary};
                border-right: 1px solid {p.border};
            }}
        """)
        self.title_label.setStyleSheet(
            f"color: {p.text_primary}; font-weight: 700; font-size: 15px; letter-spacing: 1px;"
        )
        self.subtitle_label.setStyleSheet(f"color: {p.text_muted}; font-size: 11px;")
        self._update_logo()
        for btn in self._buttons:
            btn.update_style()
        self.settings_btn.update_style()
