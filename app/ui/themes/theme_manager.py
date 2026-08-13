"""Centralized Theme Manager managing Dark/Light application themes and QSS stylesheets."""

from typing import Optional

from PySide6.QtCore import QObject, Signal

from app.config.manager import ConfigurationManager
from app.logging import logger
from app.ui.themes.color_tokens import DARK_PALETTE, LIGHT_PALETTE, ColorPalette


class ThemeManager(QObject):
    """Centralized singleton theme manager for dark/light themes, typography, and QSS styling."""

    theme_changed = Signal(str)  # Emits theme name ("dark" or "light") when changed

    _instance: Optional["ThemeManager"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_manager: ConfigurationManager | None = None) -> None:
        if getattr(self, "_initialized", False):
            return

        super().__init__()
        self.config_manager = config_manager
        initial_theme = "dark"
        if self.config_manager and self.config_manager.settings:
            initial_theme = self.config_manager.settings.ui.theme

        self._current_theme: str = (
            initial_theme if initial_theme in ("dark", "light") else "dark"
        )
        self._accent_color: str | None = None
        self._ui_scaling: float = 1.0
        self._animations_enabled: bool = True
        self._window_transparency: bool = False
        self._initialized = True

    @property
    def current_theme(self) -> str:
        """Get current theme name ('dark' or 'light')."""
        return self._current_theme

    @property
    def palette(self) -> ColorPalette:
        """Get active color palette instance."""
        return DARK_PALETTE if self._current_theme == "dark" else LIGHT_PALETTE

    @property
    def ui_scaling(self) -> float:
        """Get active UI scaling factor."""
        return self._ui_scaling

    @property
    def animations_enabled(self) -> bool:
        """Check if UI smooth animations are enabled."""
        return self._animations_enabled

    @property
    def window_transparency(self) -> bool:
        """Check if window transparency glass effect is enabled."""
        return self._window_transparency

    def set_theme(self, theme_name: str) -> None:
        """Switch current theme to 'dark' or 'light'.

        Args:
            theme_name: Name of theme ('dark' or 'light').
        """
        if theme_name not in ("dark", "light"):
            logger.warning(
                f"Invalid theme name requested: '{theme_name}'. Defaulting to 'dark'."
            )
            theme_name = "dark"

        if self._current_theme == theme_name:
            return

        self._current_theme = theme_name
        logger.info(f"Theme switched to: '{self._current_theme}'.")

        # Update persisted configuration if manager available
        if self.config_manager and self.config_manager.settings:
            self.config_manager.settings.ui.theme = self._current_theme

        self.theme_changed.emit(self._current_theme)

    def toggle_theme(self) -> str:
        """Toggle between dark and light theme."""
        new_theme = "light" if self._current_theme == "dark" else "dark"
        self.set_theme(new_theme)
        return self._current_theme

    def set_ui_scaling(self, scaling: float) -> None:
        """Set UI scaling factor."""
        self._ui_scaling = max(0.8, min(2.0, scaling))
        self.theme_changed.emit(self._current_theme)

    def set_animations_enabled(self, enabled: bool) -> None:
        """Enable or disable smooth UI animations."""
        self._animations_enabled = enabled
        self.theme_changed.emit(self._current_theme)

    def set_window_transparency(self, enabled: bool) -> None:
        """Enable or disable window transparency glass effect."""
        self._window_transparency = enabled
        self.theme_changed.emit(self._current_theme)

    def get_stylesheet(self) -> str:
        """Generate global PySide6 QSS stylesheet for active theme."""
        p = self.palette
        return f"""
        QMainWindow, QDialog, QWidget#CentralWidget {{
            background-color: {p.bg_primary};
            color: {p.text_primary};
            font-family: 'Segoe UI', 'Inter', -apple-system, sans-serif;
            font-size: 13px;
        }}

        QWidget {{
            color: {p.text_primary};
        }}

        /* ScrollBar Styling */
        QScrollBar:vertical {{
            border: none;
            background: {p.bg_secondary};
            width: 8px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {p.border_light};
            min-height: 20px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {p.accent};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        /* ToolTips */
        QToolTip {{
            background-color: {p.bg_card};
            color: {p.text_primary};
            border: 1px solid {p.border};
            padding: 5px 8px;
            border-radius: 4px;
        }}
        """
