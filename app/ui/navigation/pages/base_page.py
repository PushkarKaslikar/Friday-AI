"""Base page template for navigation views."""

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ui.themes.theme_manager import ThemeManager


class BasePage(QWidget):
    """Abstract base page layout providing consistent header and content scrolling container."""

    def __init__(
        self,
        title: str,
        subtitle: str,
        theme_manager: ThemeManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.title_text = title
        self.subtitle_text = subtitle
        self.theme_manager = theme_manager or ThemeManager()

        self._setup_base_ui()
        self.theme_manager.theme_changed.connect(lambda _: self._update_page_styles())

    def _setup_base_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(20)

        # Page Header
        header_container = QWidget(self)
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        self.title_label = QLabel(self.title_text, header_container)
        self.subtitle_label = QLabel(self.subtitle_text, header_container)

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)

        main_layout.addWidget(header_container)

        # Scrollable Content Body Area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(16)

        self.scroll_area.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll_area)

        self._update_page_styles()

    def _update_page_styles(self) -> None:
        p = self.theme_manager.palette
        self.title_label.setStyleSheet(
            f"color: {p.text_primary}; font-size: 22px; font-weight: 700;"
        )
        self.subtitle_label.setStyleSheet(
            f"color: {p.text_secondary}; font-size: 13px;"
        )
        self.setStyleSheet(f"background-color: {p.bg_primary};")
        self.content_widget.setStyleSheet(f"background-color: {p.bg_primary};")
