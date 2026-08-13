"""Home Page view placeholder displaying assistant dashboard metrics and quick launcher."""

from PySide6.QtWidgets import QGridLayout, QWidget

from app.ui.navigation.pages.base_page import BasePage
from app.ui.widgets.card import FridayCard


class HomePage(BasePage):
    """Home Dashboard overview page."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Overview & Status",
            subtitle="Friday Personal AI Desktop Assistant is active in the background.",
            parent=parent,
        )
        self._populate_content()

    def _populate_content(self) -> None:
        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)

        cards = [
            (
                "Local Reasoning Engine",
                "Phase 1.2 Desktop Shell Active. Ready for local LLM inference integration in future phase.",
                "assistant",
            ),
            (
                "Desktop & System Tray",
                "Running in background tray mode with sub-second native Windows lifecycle control.",
                "home",
            ),
            (
                "Memory & Preference System",
                "Foundational Clean Architecture layer ready for localized vector memory store.",
                "memory",
            ),
            (
                "Automation Workflows",
                "Event-driven architecture prepared for OS and browser execution triggers.",
                "automation",
            ),
        ]

        for idx, (title, desc, icon) in enumerate(cards):
            card = FridayCard(title=title, description=desc, icon_name=icon)
            row = idx // 2
            col = idx % 2
            grid_layout.addWidget(card, row, col)

        self.content_layout.addLayout(grid_layout)
        self.content_layout.addStretch()
