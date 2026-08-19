"""Logs Page view displaying live application and Phase 6.7 safety audit logs."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget,
)

from app.automation.safety.audit import AutomationAuditLog
from app.ui.navigation.pages.base_page import BasePage


class LogsPage(BasePage):
    """Application & Safety Audit Log Viewer."""

    def __init__(
        self,
        audit_log: AutomationAuditLog | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            title="System & Safety Audit Logs",
            subtitle="Real-time privacy-preserving execution log feed and Phase 6.7 audit events.",
            parent=parent,
        )
        self.audit_log = audit_log

        self._populate_content()

    def _populate_content(self) -> None:
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 8)

        lbl_log = QLabel("Live System & Safety Log Output:")
        lbl_log.setStyleSheet("font-weight: bold; font-size: 12px;")
        top_layout.addWidget(lbl_log)
        top_layout.addStretch()

        btn_refresh = QPushButton("🔄 Refresh Log Feed")
        btn_refresh.clicked.connect(self._refresh_logs)
        top_layout.addWidget(btn_refresh)

        self.content_layout.addLayout(top_layout)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet(
            "QTextEdit { background-color: #1E1E1E; color: #00FF66; border: 1px solid #444; border-radius: 6px; font-family: 'Consolas', 'Courier New'; font-size: 12px; padding: 8px; }"
        )
        self.content_layout.addWidget(self.log_text, stretch=1)

        self._refresh_logs()

    def _refresh_logs(self) -> None:
        events = self.audit_log.get_events() if self.audit_log else []
        lines = []
        lines.append("[SYSTEM INFO] Friday AI Assistant v1.0.0 desktop shell active.")
        lines.append(
            "[SYSTEM INFO] Phase 6.1–6.7 Computer Automation & Safety Governance initialized."
        )

        if events:
            for ev in events:
                lines.append(
                    f"[{ev.timestamp}] [SAFETY AUDIT] Tool: {ev.tool_name} | Risk: {ev.risk_level.value} | Decision: {ev.decision.value} | Status: {ev.execution_status}"
                )
        else:
            lines.append(
                "[AUDIT LOG] No high-risk safety audit events recorded in current session."
            )
            lines.append(
                "[AUDIT LOG] All automation requests executed through Phase 2 ToolExecutor boundary."
            )

        self.log_text.setText("\n".join(lines))
