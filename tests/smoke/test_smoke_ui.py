"""Smoke test verifying PySide6 UI framework initialization."""

import sys

from PySide6.QtWidgets import QApplication

from app.ui.managers.window_manager import WindowManager
from app.ui.navigation.navigation_manager import NavigationManager
from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager
from app.ui.windows.main_window import MainWindow


def test_smoke_ui_framework():
    app = QApplication.instance() or QApplication(sys.argv)
    assert app is not None

    tm = ThemeManager()
    am = AssetManager()
    nm = NavigationManager()
    wm = WindowManager()

    mw = MainWindow(
        theme_manager=tm, asset_manager=am, navigation_manager=nm, window_manager=wm
    )
    assert mw is not None
    assert mw.windowTitle() == "Friday AI Assistant"
    mw.close()
