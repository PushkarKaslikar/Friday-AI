"""Memory View placeholder."""

from PySide6.QtWidgets import QWidget

from app.ui.navigation.pages.base_page import BasePage
from app.ui.widgets.card import FridayCard


class MemoryPage(BasePage):
    """Memory & Knowledge Base View placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Memory & User Preferences",
            subtitle="Local knowledge graph and persistent contextual memory storage placeholder.",
            parent=parent,
        )
        self._populate_content()

    def _populate_content(self) -> None:
        card = FridayCard(
            title="Personalized Vector Memory Store (Future Phase)",
            description="View, edit, and organize Friday's learned user preferences and contextual memory records.",
            icon_name="memory",
        )
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()
