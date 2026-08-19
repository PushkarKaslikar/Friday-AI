"""Main Application Window for Friday AI Assistant."""

from typing import Any
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.constants.application import APP_NAME
from app.logging import logger
from app.ui.managers.window_manager import WindowManager
from app.ui.navigation.navigation_manager import NavigationManager
from app.ui.navigation.pages import (
    AssistantPage,
    AutomationPage,
    DiagnosticsPage,
    HomePage,
    LogsPage,
    MemoryPage,
    PluginsPage,
)
from app.ui.navigation.sidebar import SidebarWidget
from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager
from app.ui.widgets.header_bar import HeaderBar
from app.ui.widgets.status_bar import FridayStatusBar
from app.ui.windows.settings_window import SettingsWindow


class MainWindow(QMainWindow):
    """Main application desktop window for Friday AI Assistant."""

    def __init__(
        self,
        theme_manager: ThemeManager | None = None,
        asset_manager: AssetManager | None = None,
        navigation_manager: NavigationManager | None = None,
        window_manager: WindowManager | None = None,
        tool_executor: Any | None = None,
        tool_registry: Any | None = None,
        safety_manager: Any | None = None,
        audit_log: Any | None = None,
        container: Any | None = None,
    ) -> None:
        super().__init__()
        self.theme_manager = theme_manager or ThemeManager()
        self.asset_manager = asset_manager or AssetManager()
        self.navigation_manager = navigation_manager or NavigationManager()
        self.window_manager = window_manager or WindowManager()
        self.tool_executor = tool_executor
        self.tool_registry = tool_registry
        self.safety_manager = safety_manager
        self.audit_log = audit_log
        self.container = container

        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)
        self.setMinimumSize(1024, 728)

        self._setup_ui()
        self._set_app_icon()

        # Connect signals
        self.navigation_manager.page_changed.connect(self._on_page_changed)
        self.theme_manager.theme_changed.connect(lambda _: self._update_styles())

        logger.info("MainWindow initialized successfully.")

    def _setup_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header Bar
        self.header_bar = HeaderBar(
            title=APP_NAME,
            theme_manager=self.theme_manager,
            asset_manager=self.asset_manager,
            parent=self,
        )
        self.header_bar.minimize_clicked.connect(self.hide)
        self.header_bar.close_clicked.connect(self.hide)
        self.header_bar.settings_clicked.connect(self.open_settings)
        main_layout.addWidget(self.header_bar)

        # Body (Sidebar + Stacked Content Pages)
        body_widget = QWidget(central_widget)
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Sidebar Navigation Widget
        self.sidebar = SidebarWidget(
            navigation_manager=self.navigation_manager,
            theme_manager=self.theme_manager,
            asset_manager=self.asset_manager,
            parent=self,
        )
        self.sidebar.settings_clicked.connect(self.open_settings)
        body_layout.addWidget(self.sidebar)

        # Stacked Pages Container
        self.page_stack = QStackedWidget(body_widget)

        self.page_stack.addWidget(
            HomePage(
                tool_registry=self.tool_registry,
                safety_manager=self.safety_manager,
                parent=self.page_stack,
            )
        )
        self.page_stack.addWidget(
            AssistantPage(
                tool_executor=self.tool_executor,
                safety_manager=self.safety_manager,
                theme_manager=self.theme_manager,
                container=self.container,
                parent=self.page_stack,
            )
        )
        self.page_stack.addWidget(MemoryPage(parent=self.page_stack))
        self.page_stack.addWidget(
            AutomationPage(
                tool_registry=self.tool_registry,
                safety_manager=self.safety_manager,
                parent=self.page_stack,
            )
        )
        self.page_stack.addWidget(PluginsPage(parent=self.page_stack))
        self.page_stack.addWidget(
            LogsPage(audit_log=self.audit_log, parent=self.page_stack)
        )
        self.page_stack.addWidget(
            DiagnosticsPage(safety_manager=self.safety_manager, parent=self.page_stack)
        )

        body_layout.addWidget(self.page_stack)
        main_layout.addWidget(body_widget)

        # Status Bar
        self.status_bar = FridayStatusBar(
            theme_manager=self.theme_manager,
            parent=self,
        )
        main_layout.addWidget(self.status_bar)

        self._update_styles()

    def _set_app_icon(self) -> None:
        p = self.theme_manager.palette
        icon = self.asset_manager.get_icon("app_logo", color=p.accent, size=32)
        self.setWindowIcon(icon)

    def _on_page_changed(self, index: int, key: str) -> None:
        if 0 <= index < self.page_stack.count():
            self.page_stack.setCurrentIndex(index)
            self.status_bar.set_status_message(f"Tab switched to: '{key.capitalize()}'")
            logger.info(f"Main view navigated to tab index {index} ('{key}').")

    def open_settings(self) -> None:
        """Open settings dialog window, focusing if already open."""
        if self.window_manager.is_window_open("settings"):
            self.window_manager.show_window("settings")
            return

        settings_win = SettingsWindow(
            theme_manager=self.theme_manager,
            asset_manager=self.asset_manager,
            parent=self,
        )
        self.window_manager.register_window("settings", settings_win)
        settings_win.exec()
        self.window_manager.close_window("settings")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Intercept close event to minimize to system tray instead of exiting process."""
        event.ignore()
        self.hide()
        logger.info("MainWindow close event intercepted: minimized to system tray.")

    def _update_styles(self) -> None:
        p = self.theme_manager.palette
        self.setStyleSheet(f"""
            QMainWindow, QWidget#CentralWidget {{
                background-color: {p.bg_primary};
            }}
        """)
        self._set_app_icon()
