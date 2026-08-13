"""Automation View placeholder."""

from PySide6.QtWidgets import QWidget

from app.ui.navigation.pages.base_page import BasePage
from app.ui.widgets.card import FridayCard


class AutomationPage(BasePage):
    """Desktop Automation View placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Automation & Workflows",
            subtitle="Windows OS automation, scheduled tasks, and shortcut triggers placeholder.",
            parent=parent,
        )
        self._populate_content()

    def _populate_content(self) -> None:
        card = FridayCard(
            title="Desktop Automation Subsystem (Future Phase)",
            description="Manage background scheduled tasks, Windows hotkeys, and automated macro routines.",
            icon_name="automation",
        )
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()
