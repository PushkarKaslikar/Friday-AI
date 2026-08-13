"""Unit tests for ThemeManager."""

from app.ui.themes.theme_manager import ThemeManager


def test_theme_manager_toggle():
    tm = ThemeManager()
    initial_theme = tm.current_theme

    toggled_theme = tm.toggle_theme()
    assert toggled_theme != initial_theme
    assert tm.current_theme in ("dark", "light")

    palette = tm.palette
    assert palette.accent != ""
    assert palette.bg_primary != ""

    stylesheet = tm.get_stylesheet()
    assert "QMainWindow" in stylesheet
