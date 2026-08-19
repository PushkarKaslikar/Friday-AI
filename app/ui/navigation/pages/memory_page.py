"""Memory Page view displaying user profile, preferences, and FAISS vector index status."""

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QListWidget,
    QWidget,
)

from app.ui.navigation.pages.base_page import BasePage
from app.ui.widgets.card import FridayCard


class MemoryPage(BasePage):
    """Personal Memory & Preference Management Subsystem."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Personal Memory & Context Store",
            subtitle="Phase 5 SQLite Long-Term Memory, User Profile Service, and FAISS Local Vector Index.",
            parent=parent,
        )
        self._populate_content()

    def _populate_content(self) -> None:
        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)

        cards = [
            (
                "User Profile Snapshot",
                "Name: Pushkar | Preferred Editor: VS Code | Shell: PowerShell | System: Windows Native.",
                "memory",
            ),
            (
                "FAISS Vector Index",
                "Local embedding provider active. Fast semantic search across conversation entries.",
                "assistant",
            ),
        ]

        for idx, (title, desc, icon) in enumerate(cards):
            card = FridayCard(title=title, description=desc, icon_name=icon)
            grid_layout.addWidget(card, 0, idx)

        self.content_layout.addLayout(grid_layout)

        lbl_mem = QLabel("Recent Stored Context Memories:")
        lbl_mem.setStyleSheet("font-weight: bold; font-size: 12px; margin-top: 12px;")
        self.content_layout.addWidget(lbl_mem)

        self.mem_list = QListWidget()
        self.mem_list.setStyleSheet(
            "QListWidget { border: 1px solid #444; border-radius: 6px; padding: 6px; font-size: 12px; }"
        )

        entries = [
            "• [PROFILE] User preferred code editor set to VS Code",
            "• [PROFILE] User preferred shell environment set to PowerShell",
            "• [PROJECT] Workspace root set to 'd:\\Friday AI'",
            "• [MEMORY] Phase 6.7 Safety Governance configuration saved locally",
            "• [SECURITY] Local SQLite memory store encrypted with zero cloud sync",
        ]
        for e in entries:
            self.mem_list.addItem(e)

        self.content_layout.addWidget(self.mem_list, stretch=1)
