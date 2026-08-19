"""Automation Page view displaying registered automation tools and emergency safety controls."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QWidget,
)

from app.automation.safety.controller import AutomationSafetyManager
from app.tools.registry.tool_registry import ToolRegistry
from app.ui.navigation.pages.base_page import BasePage


class AutomationPage(BasePage):
    """Computer Automation Control Center & Safety Controls."""

    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        safety_manager: AutomationSafetyManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            title="Computer Automation Control Center",
            subtitle="Phases 6.1–6.6 UIA, Input, Window, Screen, Clipboard, App & Terminal tools with 6.7 Safety Governance.",
            parent=parent,
        )
        self.tool_registry = tool_registry
        self.safety_manager = safety_manager

        self._populate_content()

    def _populate_content(self) -> None:
        # Top Safety Governance Panel
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 12)
        top_layout.setSpacing(12)

        st = self.safety_manager.state.value if self.safety_manager else "READY"
        ks = (
            self.safety_manager.kill_switch.status.value
            if self.safety_manager
            else "ARMED"
        )

        self.lbl_status = QLabel(
            f"Safety State: {st} | Kill Switch: {ks} | Failsafe: ARMED"
        )
        self.lbl_status.setStyleSheet("font-weight: bold; font-size: 13px;")
        top_layout.addWidget(self.lbl_status)
        top_layout.addStretch()

        # Emergency Stop Button
        self.btn_kill = QPushButton("🚨 EMERGENCY STOP")
        self.btn_kill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kill.setStyleSheet(
            "QPushButton { background-color: #D32F2F; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px; }"
            "QPushButton:hover { background-color: #B71C1C; }"
        )
        self.btn_kill.clicked.connect(self._on_emergency_stop)
        top_layout.addWidget(self.btn_kill)

        # Lockdown Toggle
        self.btn_lockdown = QPushButton("🔒 Toggle Lockdown Mode")
        self.btn_lockdown.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_lockdown.setStyleSheet(
            "QPushButton { background-color: #455A64; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px; }"
        )
        self.btn_lockdown.clicked.connect(self._on_toggle_lockdown)
        top_layout.addWidget(self.btn_lockdown)

        self.content_layout.addLayout(top_layout)

        # Tools List Section
        lbl_tools = QLabel("Registered Computer Automation Tools:")
        lbl_tools.setStyleSheet("font-weight: bold; font-size: 12px;")
        self.content_layout.addWidget(lbl_tools)

        self.tools_list = QListWidget()
        self.tools_list.setStyleSheet(
            "QListWidget { border: 1px solid #444; border-radius: 6px; padding: 6px; font-size: 12px; }"
        )

        tools = self.tool_registry.list_tools() if self.tool_registry else []
        if tools:
            for t in tools:
                tool_id = getattr(t, "tool_id", getattr(t, "id", "tool"))
                meta = getattr(t, "metadata", t)
                desc = getattr(meta, "description", "")
                cat_val = (
                    meta.category.value
                    if hasattr(meta, "category") and hasattr(meta.category, "value")
                    else "AUTOMATION"
                )
                risk_val = (
                    meta.risk_level.value
                    if hasattr(meta, "risk_level")
                    and hasattr(meta.risk_level, "value")
                    else "LOW"
                )
                self.tools_list.addItem(
                    f"• {tool_id} [{cat_val}] — {desc} (Risk: {risk_val})"
                )
        else:
            default_tools = [
                "uia.list_windows [UIA] — Enumerate desktop windows (Risk: LOW)",
                "uia.inspect_window [UIA] — Inspect UI tree nodes (Risk: LOW)",
                "uia.find_element [UIA] — Locate specific UI control (Risk: LOW)",
                "input.mouse_click [INPUT] — Execute physical mouse click (Risk: MEDIUM)",
                "input.type_text [INPUT] — Type text string (Risk: HIGH)",
                "input.press_hotkey [INPUT] — Trigger key combinations (Risk: MEDIUM)",
                "window.list_open [WINDOW] — List visible open windows (Risk: LOW)",
                "window.focus [WINDOW] — Focus target window (Risk: MEDIUM)",
                "screen.capture [SCREEN] — Capture desktop screenshot (Risk: MEDIUM)",
                "clipboard.get_content [CLIPBOARD] — Read clipboard content (Risk: MEDIUM)",
                "clipboard.set_content [CLIPBOARD] — Write clipboard text (Risk: MEDIUM)",
                "application.launch [APPLICATION] — Launch desktop app (Risk: HIGH)",
                "explorer.navigate [EXPLORER] — Navigate File Explorer (Risk: MEDIUM)",
                "terminal.launch [TERMINAL] — Launch PowerShell/CMD (Risk: HIGH)",
                "workflow.execute_sequence [WORKFLOW] — Execute multi-step sequence (Risk: HIGH)",
            ]
            for dt in default_tools:
                self.tools_list.addItem(dt)

        self.content_layout.addWidget(self.tools_list, stretch=1)

    def _on_emergency_stop(self) -> None:
        if self.safety_manager:
            self.safety_manager.trigger_kill_switch("UI Emergency Stop button clicked")
            st = self.safety_manager.state.value
            ks = self.safety_manager.kill_switch.status.value
            self.lbl_status.setText(
                f"Safety State: {st} | Kill Switch: {ks} | Failsafe: ARMED"
            )

    def _on_toggle_lockdown(self) -> None:
        if self.safety_manager:
            current_mode = self.safety_manager.policy.mode.value
            new_lockdown = current_mode != "LOCKDOWN"
            self.safety_manager.set_lockdown(new_lockdown)
            st = self.safety_manager.state.value
            ks = self.safety_manager.kill_switch.status.value
            self.lbl_status.setText(
                f"Safety State: {st} | Kill Switch: {ks} | Failsafe: ARMED"
            )
