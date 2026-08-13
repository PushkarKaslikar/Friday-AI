"""Unit tests for WindowManager."""

from PySide6.QtWidgets import QWidget

from app.ui.managers.window_manager import WindowManager


def test_window_manager_lifecycle(qapp):
    wm = WindowManager()
    dummy_win = QWidget()

    wm.register_window("test_key", dummy_win)
    assert wm.get_window("test_key") == dummy_win

    wm.show_window("test_key")
    assert wm.is_window_open("test_key") is True

    wm.hide_window("test_key")
    assert wm.is_window_open("test_key") is False

    wm.close_window("test_key")
    assert wm.get_window("test_key") is None
