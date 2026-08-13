"""System Tray Manager handling application notification tray icon and context menu."""

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from app.logging import logger
from app.ui.resources.asset_manager import AssetManager


class TrayManager(QObject):
    """Manages system tray icon, context menu actions, and background state."""

    show_requested = Signal()
    hide_requested = Signal()
    settings_requested = Signal()
    restart_requested = Signal()
    exit_requested = Signal()

    def __init__(
        self,
        app_name: str = "Friday AI Assistant",
        asset_manager: AssetManager | None = None,
    ) -> None:
        super().__init__()
        self.app_name = app_name
        self.asset_manager = asset_manager or AssetManager()

        self._tray_icon: QSystemTrayIcon | None = None
        self._context_menu: QMenu | None = None

    def setup_tray(self) -> bool:
        """Initialize system tray icon and attach context menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.warning("System tray is not available on this platform.")
            return False

        icon = self.asset_manager.get_icon("app_logo", color="#6366F1", size=32)

        self._tray_icon = QSystemTrayIcon(icon)
        self._tray_icon.setToolTip(self.app_name)

        # Context Menu
        self._context_menu = QMenu()
        self._build_context_menu()
        self._tray_icon.setContextMenu(self._context_menu)

        # Double click action
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()

        logger.info("System tray initialized and visible.")
        return True

    def _build_context_menu(self) -> None:
        """Build native context menu for system tray icon."""
        assert self._context_menu is not None

        show_action = QAction("Show Friday", self._context_menu)
        show_action.triggered.connect(lambda: self.show_requested.emit())

        hide_action = QAction("Hide Friday", self._context_menu)
        hide_action.triggered.connect(lambda: self.hide_requested.emit())

        settings_action = QAction("Settings...", self._context_menu)
        settings_action.triggered.connect(lambda: self.settings_requested.emit())

        restart_action = QAction("Restart Assistant", self._context_menu)
        restart_action.triggered.connect(lambda: self.restart_requested.emit())

        exit_action = QAction("Exit Friday", self._context_menu)
        exit_action.triggered.connect(lambda: self.exit_requested.emit())

        self._context_menu.addAction(show_action)
        self._context_menu.addAction(hide_action)
        self._context_menu.addSeparator()
        self._context_menu.addAction(settings_action)
        self._context_menu.addSeparator()
        self._context_menu.addAction(restart_action)
        self._context_menu.addAction(exit_action)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon click activation."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.show_requested.emit()

    def show_notification(self, title: str, message: str, msec: int = 3000) -> None:
        """Display system tray balloon notification message."""
        if self._tray_icon and self._tray_icon.isVisible():
            self._tray_icon.showMessage(
                title, message, QSystemTrayIcon.MessageIcon.Information, msec
            )

    def hide(self) -> None:
        """Hide system tray icon."""
        if self._tray_icon:
            self._tray_icon.hide()
