"""Diagnostics View placeholder."""

from PySide6.QtWidgets import QWidget

from app.ui.navigation.pages.base_page import BasePage
from app.ui.widgets.card import FridayCard


class DiagnosticsPage(BasePage):
    """System Health & Diagnostics View placeholder."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="System Diagnostics & Performance",
            subtitle="CPU, RAM, GPU, and runtime latency monitoring placeholder.",
            parent=parent,
        )
        self._populate_content()

    def _populate_content(self) -> None:
        card = FridayCard(
            title="System Resource Inspector",
            description="Real-time monitoring of desktop memory consumption, background CPU utilization, and system state.",
            icon_name="diagnostics",
        )
        self.content_layout.addWidget(card)
        self.content_layout.addStretch()
