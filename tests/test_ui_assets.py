"""Unit tests for AssetManager."""

from PySide6.QtGui import QIcon, QPixmap

from app.ui.resources.asset_manager import AssetManager


def test_asset_manager_icon_rendering(qapp):
    am = AssetManager()
    icon = am.get_icon("home", color="#6366F1", size=24)
    assert isinstance(icon, QIcon)

    pixmap = am.get_pixmap("app_logo", color="#6366F1", size=32)
    assert isinstance(pixmap, QPixmap)
    assert not pixmap.isNull()
    assert pixmap.width() == 32
