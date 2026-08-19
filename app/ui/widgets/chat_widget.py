"""Interactive Chat, Prompt Input, and Safety Confirmation Widgets for Friday UI."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.automation.safety.models import AutomationConfirmationRequest
from app.ui.resources.asset_manager import AssetManager
from app.ui.themes.theme_manager import ThemeManager


class ChatMessageWidget(QFrame):
    """Speech/Chat bubble widget for rendering conversation messages and tool execution badges."""

    def __init__(
        self,
        sender: str,
        text: str,
        timestamp: str = "",
        tool_badge: str | None = None,
        risk_level: str | None = None,
        theme_manager: ThemeManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.theme_manager = theme_manager or ThemeManager()
        self.sender_name = sender
        self.text_content = text
        self.timestamp = timestamp
        self.tool_badge = tool_badge
        self.risk_level = risk_level

        self._setup_ui()

    def _setup_ui(self) -> None:
        p = self.theme_manager.palette
        is_user = self.sender_name.lower() in ("user", "you")

        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setLineWidth(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Header Row: Sender + Timestamp + Optional Badges
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        lbl_sender = QLabel(self.sender_name)
        f_sender = QFont("Segoe UI", 10, QFont.Weight.Bold)
        lbl_sender.setFont(f_sender)
        lbl_sender.setStyleSheet(f"color: {p.accent if is_user else p.text_primary};")
        header_layout.addWidget(lbl_sender)

        if self.tool_badge:
            lbl_badge = QLabel(f" Tool: {self.tool_badge} ")
            lbl_badge.setStyleSheet(
                f"background-color: {p.bg_hover}; color: {p.text_secondary}; "
                f"border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 600;"
            )
            header_layout.addWidget(lbl_badge)

        if self.risk_level:
            color = (
                p.accent
                if self.risk_level in ("HIGH", "CRITICAL")
                else p.text_secondary
            )
            lbl_risk = QLabel(f" Risk: {self.risk_level} ")
            lbl_risk.setStyleSheet(
                f"background-color: {color}; color: #FFFFFF; "
                f"border-radius: 4px; padding: 2px 6px; font-size: 11px; font-weight: 700;"
            )
            header_layout.addWidget(lbl_risk)

        header_layout.addStretch()

        if self.timestamp:
            lbl_time = QLabel(self.timestamp)
            lbl_time.setStyleSheet(f"color: {p.text_secondary}; font-size: 11px;")
            header_layout.addWidget(lbl_time)

        layout.addLayout(header_layout)

        # Message Text
        lbl_text = QLabel(self.text_content)
        lbl_text.setWordWrap(True)
        lbl_text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl_text.setStyleSheet(
            f"color: {p.text_primary}; font-size: 13px; line-height: 1.4;"
        )
        layout.addWidget(lbl_text)

        # Container styling
        bg = p.bg_hover if is_user else p.bg_card
        border = p.accent if is_user else p.border
        self.setStyleSheet(
            f"QFrame {{ background-color: {bg}; border: 1px solid {border}; border-radius: 8px; }}"
        )


class ChatPromptInputWidget(QWidget):
    """Input control bar with text input field, send button, voice toggle, and quick action bar."""

    send_requested = Signal(str)
    voice_toggled = Signal(bool)
    action_triggered = Signal(str)

    def __init__(
        self,
        theme_manager: ThemeManager | None = None,
        asset_manager: AssetManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.theme_manager = theme_manager or ThemeManager()
        self.asset_manager = asset_manager or AssetManager()
        self._is_listening = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        p = self.theme_manager.palette
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.setSpacing(8)

        # Quick Action Shortcuts Bar
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)

        lbl_quick = QLabel("Quick Actions:")
        lbl_quick.setStyleSheet(
            f"color: {p.text_secondary}; font-size: 11px; font-weight: 600;"
        )
        actions_layout.addWidget(lbl_quick)

        quick_cmds = [
            ("List Open Windows", "window.list_open"),
            ("Capture Screen", "screen.capture"),
            ("Safety Status", "safety.status"),
            ("System Health", "diagnostics.health"),
        ]

        for label, cmd_key in quick_cmds:
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {p.bg_secondary}; color: {p.text_primary}; "
                f"border: 1px solid {p.border}; border-radius: 4px; padding: 4px 8px; font-size: 11px; }}"
                f"QPushButton:hover {{ background-color: {p.accent}; color: #FFFFFF; }}"
            )
            btn.clicked.connect(lambda _, k=cmd_key: self.action_triggered.emit(k))
            actions_layout.addWidget(btn)

        actions_layout.addStretch()
        main_layout.addLayout(actions_layout)

        # Prompt Input Row: Text Field + Send + Voice Toggle
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(
            "Ask Friday anything or enter computer automation command..."
        )
        self.input_field.setStyleSheet(
            f"QLineEdit {{ background-color: {p.bg_card}; color: {p.text_primary}; "
            f"border: 1px solid {p.border}; border-radius: 6px; padding: 8px 12px; font-size: 13px; }}"
            f"QLineEdit:focus {{ border: 1px solid {p.accent}; }}"
        )
        self.input_field.returnPressed.connect(self._on_send_clicked)
        input_layout.addWidget(self.input_field, stretch=1)

        self.btn_send = QPushButton("Send")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.setStyleSheet(
            f"QPushButton {{ background-color: {p.accent}; color: #FFFFFF; font-weight: 600; "
            f"border: none; border-radius: 6px; padding: 8px 16px; font-size: 13px; }}"
            f"QPushButton:hover {{ opacity: 0.9; }}"
        )
        self.btn_send.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.btn_send)

        self.btn_voice = QPushButton("🎤 Voice")
        self.btn_voice.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_voice.setStyleSheet(
            f"QPushButton {{ background-color: {p.bg_secondary}; color: {p.text_primary}; "
            f"border: 1px solid {p.border}; border-radius: 6px; padding: 8px 12px; font-size: 13px; }}"
        )
        self.btn_voice.clicked.connect(self._on_voice_toggled)
        input_layout.addWidget(self.btn_voice)

        main_layout.addLayout(input_layout)

    def _on_send_clicked(self) -> None:
        text = self.input_field.text().strip()
        if text:
            self.input_field.clear()
            self.send_requested.emit(text)

    def _on_voice_toggled(self) -> None:
        self._is_listening = not self._is_listening
        p = self.theme_manager.palette
        if self._is_listening:
            self.btn_voice.setText("🔴 Listening...")
            self.btn_voice.setStyleSheet(
                f"QPushButton {{ background-color: {p.accent}; color: #FFFFFF; font-weight: bold; "
                f"border: none; border-radius: 6px; padding: 8px 12px; font-size: 13px; }}"
            )
        else:
            self.btn_voice.setText("🎤 Voice")
            self.btn_voice.setStyleSheet(
                f"QPushButton {{ background-color: {p.bg_secondary}; color: {p.text_primary}; "
                f"border: 1px solid {p.border}; border-radius: 6px; padding: 8px 12px; font-size: 13px; }}"
            )
        self.voice_toggled.emit(self._is_listening)


class ConfirmationModalWidget(QFrame):
    """Interactive card dialog rendering structured user confirmation requests."""

    confirmed_signal = Signal(str, bool)

    def __init__(
        self,
        request: AutomationConfirmationRequest,
        theme_manager: ThemeManager | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.request = request
        self.theme_manager = theme_manager or ThemeManager()

        self._setup_ui()

    def _setup_ui(self) -> None:
        p = self.theme_manager.palette
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"QFrame {{ background-color: {p.bg_card}; border: 2px solid {p.accent}; border-radius: 8px; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Header Title
        lbl_title = QLabel("⚠️ High-Risk Action Confirmation Required")
        lbl_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_title.setStyleSheet(f"color: {p.accent};")
        layout.addWidget(lbl_title)

        # Reason & Action Summary
        lbl_reason = QLabel(f"Reason: {self.request.reason}")
        lbl_reason.setWordWrap(True)
        lbl_reason.setStyleSheet(
            f"color: {p.text_primary}; font-weight: 600; font-size: 13px;"
        )
        layout.addWidget(lbl_reason)

        lbl_summary = QLabel(f"Summary: {self.request.action_summary}")
        lbl_summary.setWordWrap(True)
        lbl_summary.setStyleSheet(f"color: {p.text_secondary}; font-size: 12px;")
        layout.addWidget(lbl_summary)

        # Buttons Row: Confirm / Deny
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_deny = QPushButton("Deny Action")
        btn_deny.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_deny.setStyleSheet(
            f"QPushButton {{ background-color: {p.bg_secondary}; color: {p.text_primary}; "
            f"border: 1px solid {p.border}; border-radius: 4px; padding: 6px 12px; font-weight: 600; }}"
        )
        btn_deny.clicked.connect(
            lambda: self.confirmed_signal.emit(self.request.confirmation_id, False)
        )
        btn_layout.addWidget(btn_deny)

        btn_confirm = QPushButton("Confirm Action")
        btn_confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_confirm.setStyleSheet(
            f"QPushButton {{ background-color: {p.accent}; color: #FFFFFF; "
            f"border: none; border-radius: 4px; padding: 6px 12px; font-weight: 700; }}"
        )
        btn_confirm.clicked.connect(
            lambda: self.confirmed_signal.emit(self.request.confirmation_id, True)
        )
        btn_layout.addWidget(btn_confirm)

        layout.addLayout(btn_layout)
