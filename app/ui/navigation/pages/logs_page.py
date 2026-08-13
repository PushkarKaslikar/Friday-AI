"""Logs View placeholder."""

from PySide6.QtWidgets import QWidget

from app.ui.navigation.pages.base_page import BasePage
from app.ui.widgets.card import FridayCard


class LogsPage(BasePage):
    """Application Live Logs View placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="System Log Viewer",
            subtitle="Real-time Loguru application and error log events.",
            parent=parent,
        )
        self._populate_content()

    def _populate_content(self) -> None:
        card = FridayCard(
            title="Loguru Log Stream (Active)",
            description="Live log streaming from logs/application.log and logs/errors.log.",
            icon_name="logs",
        )
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()
