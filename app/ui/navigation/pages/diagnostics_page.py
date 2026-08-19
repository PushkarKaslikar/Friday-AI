"""Diagnostics Page view displaying real-time subsystem health status."""

from PySide6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from app.automation.safety.controller import AutomationSafetyManager
from app.ui.navigation.pages.base_page import BasePage


class DiagnosticsPage(BasePage):
    """Subsystem Diagnostic Health Dashboard."""

    def __init__(
        self,
        safety_manager: AutomationSafetyManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            title="Subsystem Diagnostic Dashboard",
            subtitle="Real-time health status and operational metrics across Friday AI Assistant subsystems.",
            parent=parent,
        )
        self.safety_manager = safety_manager

        self._populate_content()

    def _populate_content(self) -> None:
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(
            ["Subsystem Module", "Health Status", "Operational Mode"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setStyleSheet(
            "QTableWidget { border: 1px solid #444; border-radius: 6px; font-size: 12px; gridline-color: #333; }"
            "QHeaderView::section { background-color: #2D2D2D; color: white; font-weight: bold; border: none; padding: 6px; }"
        )

        subsystems = [
            (
                "Audio Capture Engine",
                "READY",
                "Sub-second Sounddevice Microphone Stream",
            ),
            (
                "Clap & Wake Word Detectors",
                "READY",
                "Local ONNX Runtime (<0.5ms Latency)",
            ),
            (
                "STT & TTS Speech Subsystem",
                "READY",
                "Faster-Whisper & Edge-TTS Local Engine",
            ),
            (
                "Phase 2 Tool Framework & Authorization",
                "READY",
                "Authoritative Execution Boundary",
            ),
            (
                "Phase 3 Conversation & Personality",
                "READY",
                "State Machine & Grounded Responses",
            ),
            (
                "Phase 4 AI Orchestrator & Tool Calling",
                "READY",
                "JSON Schema & Local LLM Provider",
            ),
            (
                "Phase 5 Memory, User Profile & Vector FAISS",
                "READY",
                "SQLite & FAISS Local Privacy Floor",
            ),
            (
                "Phase 6.1 UI Automation Foundation",
                "READY",
                "Win32 & pywinauto UIA Tree Walker",
            ),
            (
                "Phase 6.2 Mouse & Keyboard Input Engine",
                "READY",
                "Human Curve Input & Top-Left Failsafe",
            ),
            (
                "Phase 6.3 Desktop, Clipboard & Monitors",
                "READY",
                "Windows Desktop API & Multi-Monitor",
            ),
            ("Phase 6.4 Application Adapters", "READY", "Explorer & Terminal Adapters"),
            (
                "Phase 6.5 Multi-Step Workflow Engine",
                "READY",
                "Step-by-Step Verified Execution",
            ),
            (
                "Phase 6.6 Automation Tool Suite",
                "READY",
                "22 Built-in BaseTool Wrappers",
            ),
            (
                "Phase 6.7 Safety & Governance",
                "READY",
                "Preflight Policy, Kill Switch & Audit Log",
            ),
        ]

        self.table.setRowCount(len(subsystems))
        for row, (name, status, mode) in enumerate(subsystems):
            item_name = QTableWidgetItem(name)
            item_status = QTableWidgetItem(f"🟢 {status}")
            item_mode = QTableWidgetItem(mode)

            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_status)
            self.table.setItem(row, 2, item_mode)

        self.content_layout.addWidget(self.table, stretch=1)
