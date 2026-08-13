"""Plugins View placeholder."""

from PySide6.QtWidgets import QWidget

from app.ui.navigation.pages.base_page import BasePage
from app.ui.widgets.card import FridayCard


class PluginsPage(BasePage):
    """Plugins & Extensions View placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Plugin Ecosystem",
            subtitle="Modular extension management placeholder for expanding Friday capabilities.",
            parent=parent,
        )
        self._populate_content()

    def _populate_content(self) -> None:
        card = FridayCard(
            title="Plugin Architecture (Future Phase)",
            description="Enable or disable modular third-party integrations, WhatsApp automation, and custom tools.",
            icon_name="plugins",
        )
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()
