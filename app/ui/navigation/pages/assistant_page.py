"""Assistant View placeholder."""

from PySide6.QtWidgets import QWidget

from app.ui.navigation.pages.base_page import BasePage
from app.ui.widgets.card import FridayCard


class AssistantPage(BasePage):
    """Assistant Interaction View placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Assistant Conversation & Controls",
            subtitle="Local natural language processing and voice interaction interface placeholder.",
            parent=parent,
        )
        self._populate_content()

    def _populate_content(self) -> None:
        card = FridayCard(
            title="AI Interaction Subsystem (Future Phase)",
            description="This area will house local model reasoning, quick prompt inputs, and voice synthesis status indicator.",
            icon_name="assistant",
        )
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()
