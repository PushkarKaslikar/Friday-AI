"""Home Page view displaying real-time system status metrics and quick automation triggers."""

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.automation.safety.controller import AutomationSafetyManager
from app.tools.registry.tool_registry import ToolRegistry
from app.ui.navigation.pages.base_page import BasePage
from app.ui.widgets.card import FridayCard


class HomePage(BasePage):
    """Home Dashboard overview page."""

    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        safety_manager: AutomationSafetyManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            title="Overview & Status",
            subtitle="Friday Personal AI Desktop Assistant is active and governing desktop automation.",
            parent=parent,
        )
        self.tool_registry = tool_registry
        self.safety_manager = safety_manager

        self._populate_content()

    def _populate_content(self) -> None:
        tool_count = len(self.tool_registry.list_tools()) if self.tool_registry else 22
        st_val = self.safety_manager.state.value if self.safety_manager else "READY"
        ks_val = (
            self.safety_manager.kill_switch.status.value
            if self.safety_manager
            else "ARMED"
        )

        grid_layout = QGridLayout()
        grid_layout.setSpacing(16)

        cards = [
            (
                "Local AI Reasoning Engine",
                "Phase 4 AIOrchestrator & ToolCallingEngine active with local ONNX runtime.",
                "assistant",
            ),
            (
                f"Automation Tool Suite ({tool_count} Tools)",
                "Phases 6.1–6.6 UIA, Input, Window, Screen, Clipboard, App & Terminal tools registered.",
                "automation",
            ),
            (
                "Memory & User Profile",
                "Phase 5 SQLite Long-Term Memory & Local FAISS Vector Index active.",
                "memory",
            ),
            (
                f"Safety Governance ({st_val})",
                f"Phase 6.7 Safety Policy, Emergency Kill Switch ({ks_val}) & Failsafe ARMED.",
                "home",
            ),
        ]

        for idx, (title, desc, icon) in enumerate(cards):
            card = FridayCard(title=title, description=desc, icon_name=icon)
            row = idx // 2
            col = idx % 2
            grid_layout.addWidget(card, row, col)

        self.content_layout.addLayout(grid_layout)

        # Quick Control Panel Section
        panel_layout = QVBoxLayout()
        panel_layout.setContentsMargins(0, 16, 0, 0)
        panel_layout.setSpacing(8)

        lbl_panel = QLabel("Quick Automation Control Shortcuts:")
        lbl_panel.setStyleSheet("font-weight: bold; font-size: 13px;")
        panel_layout.addWidget(lbl_panel)

        btns_layout = QHBoxLayout()
        btns_layout.setSpacing(10)

        btn_inspect = QPushButton("Inspect Open Windows")
        btn_inspect.setStyleSheet("padding: 8px 14px; font-weight: 600;")
        btns_layout.addWidget(btn_inspect)

        btn_screen = QPushButton("Capture Screen Bounds")
        btn_screen.setStyleSheet("padding: 8px 14px; font-weight: 600;")
        btns_layout.addWidget(btn_screen)

        btn_safety = QPushButton("View Safety Audit Log")
        btn_safety.setStyleSheet("padding: 8px 14px; font-weight: 600;")
        btns_layout.addWidget(btn_safety)

        btns_layout.addStretch()
        panel_layout.addLayout(btns_layout)

        self.content_layout.addLayout(panel_layout)
        self.content_layout.addStretch()
