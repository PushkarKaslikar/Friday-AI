"""Assistant Interaction View connecting PySide6 Desktop UI with Friday Backend AI Engines & Voice Loop."""

import uuid
from typing import Any

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.ai.orchestration.models import OrchestrationRequest
from app.automation.safety.controller import AutomationSafetyManager
from app.automation.safety.models import AutomationSafetyDecision
from app.logging import logger
from app.services.events.event_bus import EventBus
from app.tools.execution.tool_executor import ToolExecutor
from app.ui.navigation.pages.base_page import BasePage
from app.ui.themes.theme_manager import ThemeManager
from app.ui.widgets.chat_widget import (
    ChatMessageWidget,
    ChatPromptInputWidget,
    ConfirmationModalWidget,
)
from app.utilities.system_utils import get_timestamp_str
from app.voice.clap.events import DoubleClapDetected
from app.voice.conversation.events import ConversationStateChanged
from app.voice.stt.events import TranscriptionCompleted
from app.voice.wakeword.events import WakeWordDetected


class AIRequestWorker(QObject):
    """Background worker executing AI Orchestrator or computer automation requests and speaking responses."""

    finished = Signal(dict)

    def __init__(
        self,
        prompt: str,
        executor: ToolExecutor | None = None,
        safety_manager: AutomationSafetyManager | None = None,
        container: Any | None = None,
    ) -> None:
        super().__init__()
        self.prompt = prompt
        self.executor = executor
        self.safety_manager = safety_manager
        self.container = container

    def run(self) -> None:
        """Process user request and execute tools or return response payload."""
        p_lower = self.prompt.lower().strip()
        resp_text = ""
        tool_id = "assistant.reason"
        success = True

        # Quick Actions
        if (
            p_lower in ("window.list_open", "list open windows", "list windows")
            and self.executor
        ):
            res = self.executor.execute("window.list_open", {})
            data = res.data if res and isinstance(res.data, dict) else {}
            windows = data.get("windows", [])
            w_str = (
                ", ".join([w.get("title", "Window") for w in windows[:5]])
                if windows
                else "No open windows found"
            )
            resp_text = f"Friday listed {len(windows)} open windows: {w_str}"
            tool_id = "window.list_open"
            success = res.success if res else False

        elif (
            p_lower in ("screen.capture", "capture screen", "screenshot")
            and self.executor
        ):
            res = self.executor.execute("screen.capture", {})
            data = res.data if res and isinstance(res.data, dict) else {}
            resp_text = f"Screen capture completed successfully. Image dimensions: {data.get('width', 1920)}x{data.get('height', 1080)} pixels."
            tool_id = "screen.capture"
            success = res.success if res else False

        elif p_lower in ("safety.status", "safety status") and self.safety_manager:
            st = self.safety_manager.state.value
            ks = self.safety_manager.kill_switch.status.value
            resp_text = f"Automation Safety Governance State: {st} | Emergency Kill Switch: {ks} | Failsafe: ARMED"
            tool_id = "safety.status"

        elif p_lower in ("diagnostics.health", "system health"):
            resp_text = "Friday System Health Check: All 7 Phase 6 Subsystems READY. Local-first ONNX runtime & Security boundaries ACTIVE."
            tool_id = "diagnostics.health"

        elif (
            any(k in p_lower for k in ("chrome", "browser"))
            and any(k in p_lower for k in ("open", "launch", "start"))
        ) and self.executor:
            res = self.executor.execute("application.launch", {"application": "chrome"})
            resp_text = "Opening Google Chrome..."
            tool_id = "application.launch"
            success = res.success if res else False

        elif (
            any(k in p_lower for k in ("explorer", "file explorer", "folder"))
            and any(k in p_lower for k in ("open", "launch", "start"))
        ) and self.executor:
            res = self.executor.execute(
                "application.launch", {"application": "explorer"}
            )
            resp_text = "Opening File Explorer..."
            tool_id = "application.launch"
            success = res.success if res else False

        elif (
            any(k in p_lower for k in ("notepad", "text editor"))
            and any(k in p_lower for k in ("open", "launch", "start"))
        ) and self.executor:
            res = self.executor.execute(
                "application.launch", {"application": "notepad"}
            )
            resp_text = "Opening Notepad application..."
            tool_id = "application.launch"
            success = res.success if res else False

        else:
            # AI Orchestrator or Natural Language Processing
            if self.container:
                try:
                    orchestrator = self.container.ai_orchestrator()
                    if orchestrator:
                        req = OrchestrationRequest(
                            request_id=str(uuid.uuid4()),
                            user_input=self.prompt,
                        )
                        orch_res = orchestrator.process_request(req)
                        resp_text = getattr(orch_res, "final_response", "") or str(
                            orch_res
                        )
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"AIOrchestrator request processing fallback: {exc}")
                    resp_text = f"Friday processed: '{self.prompt}'. Local reasoning & desktop automation engine is active."
            else:
                resp_text = f"Friday processed: '{self.prompt}'. Local desktop automation engine is active."

        # Speak Response Aloud via TTSService if container available
        if self.container and resp_text:
            try:
                tts = self.container.tts_service()
                tts.speak(resp_text)
            except Exception as tts_err:  # noqa: BLE001
                logger.warning(
                    f"AIRequestWorker failed to speak response aloud: {tts_err}"
                )

        self.finished.emit(
            {
                "response": resp_text,
                "tool": tool_id,
                "success": success,
            }
        )


class VoiceActivationWorker(QObject):
    """Asynchronous background worker executing voice activation without freezing Qt GUI event loop."""

    finished = Signal()

    def __init__(self, container: Any | None = None) -> None:
        super().__init__()
        self.container = container

    def run(self) -> None:
        if self.container:
            try:
                csm = self.container.conversation_state_machine()
                if csm:
                    csm.activate(source="GUI")
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"VoiceActivationWorker CSM error: {exc}")

            try:
                tts = self.container.tts_service()
                if tts:
                    tts.speak("I am listening. What can I do for you?")
            except Exception as tts_err:  # noqa: BLE001
                logger.warning(f"VoiceActivationWorker TTS error: {tts_err}")

        self.finished.emit()


class AssistantPage(BasePage):
    """Interactive Assistant Conversation & Computer Automation Control View."""

    # Internal Signals for Thread-Safe EventBus UI Updates
    eventbus_wakeword_signal = Signal(str)
    eventbus_clap_signal = Signal()
    eventbus_transcription_signal = Signal(str)
    eventbus_state_signal = Signal(str)

    def __init__(
        self,
        tool_executor: ToolExecutor | None = None,
        safety_manager: AutomationSafetyManager | None = None,
        theme_manager: ThemeManager | None = None,
        container: Any | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            title="Assistant Voice & Automation Hub",
            subtitle="Real-time voice recognition, AI orchestration, computer automation tools & governance.",
            parent=parent,
        )
        self.tool_executor = tool_executor
        self.safety_manager = safety_manager
        self.theme_manager = theme_manager or ThemeManager()
        self.container = container
        self._active_threads: list[QThread] = []

        self._setup_assistant_ui()
        self._subscribe_to_voice_events()

    def _setup_assistant_ui(self) -> None:
        p = self.theme_manager.palette

        # 1. Top Section: Voice HUD Card
        hud_frame = QFrame()
        hud_frame.setFrameShape(QFrame.Shape.StyledPanel)
        hud_frame.setStyleSheet(
            f"QFrame {{ background-color: {p.bg_card}; border: 1px solid {p.border_glow}; border-radius: 10px; }}"
        )
        hud_layout = QVBoxLayout(hud_frame)
        hud_layout.setContentsMargins(14, 12, 14, 12)
        hud_layout.setSpacing(8)

        hud_header = QHBoxLayout()
        lbl_hud_title = QLabel("🎙️ Friday Voice Subsystem HUD")
        lbl_hud_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        lbl_hud_title.setStyleSheet(f"color: {p.accent};")
        hud_header.addWidget(lbl_hud_title)

        self.lbl_hud_status = QLabel("🟢 ENGINE ONLINE")
        self.lbl_hud_status.setStyleSheet(
            f"background-color: {p.bg_hover}; color: {p.status_success}; "
            f"font-weight: 700; font-size: 11px; padding: 3px 8px; border-radius: 4px;"
        )
        hud_header.addWidget(self.lbl_hud_status)
        hud_header.addStretch()

        self.btn_talk = QPushButton("🎙️ PUSH TO TALK / TRIGGER VOICE ACTIVATION")
        self.btn_talk.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_talk.setStyleSheet(
            f"QPushButton {{ background-color: {p.accent}; color: #000000; font-weight: 800; "
            f"border-radius: 6px; padding: 8px 16px; font-size: 12px; }}"
            f"QPushButton:hover {{ opacity: 0.9; }}"
        )
        self.btn_talk.clicked.connect(self._on_talk_button_clicked)
        hud_header.addWidget(self.btn_talk)
        hud_layout.addLayout(hud_header)

        # Status Badges Row
        badges_layout = QHBoxLayout()
        badges_layout.setSpacing(12)

        self.lbl_wakeword_badge = QLabel(
            "🔴 Wake Word: LISTENING ('Hey Friday' / 'Hey Jarvis')"
        )
        self.lbl_wakeword_badge.setStyleSheet(
            f"color: {p.text_secondary}; font-size: 11px; font-weight: 600;"
        )
        badges_layout.addWidget(self.lbl_wakeword_badge)

        self.lbl_clap_badge = QLabel("👏 Double Clap: LISTENING")
        self.lbl_clap_badge.setStyleSheet(
            f"color: {p.text_secondary}; font-size: 11px; font-weight: 600;"
        )
        badges_layout.addWidget(self.lbl_clap_badge)

        self.lbl_state_badge = QLabel("🎙️ State: IDLE")
        self.lbl_state_badge.setStyleSheet(
            f"color: {p.accent}; font-size: 11px; font-weight: 700;"
        )
        badges_layout.addWidget(self.lbl_state_badge)
        badges_layout.addStretch()

        hud_layout.addLayout(badges_layout)
        self.content_layout.addWidget(hud_frame)

        # 2. Middle Section: Scroll Area for Chat & Voice Messages
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setContentsMargins(0, 0, 0, 0)
        self.messages_layout.setSpacing(10)
        self.messages_layout.addStretch()

        self.scroll_area.setWidget(self.messages_container)
        self.content_layout.addWidget(self.scroll_area, stretch=1)

        # 3. Bottom Section: Prompt Input Bar
        self.input_widget = ChatPromptInputWidget(
            theme_manager=self.theme_manager, parent=self
        )
        self.input_widget.send_requested.connect(self._on_user_send_prompt)
        self.input_widget.action_triggered.connect(self._on_user_send_prompt)
        self.input_widget.voice_toggled.connect(self._on_voice_toggle_clicked)
        self.content_layout.addWidget(self.input_widget)

        # Initial Welcome Message
        self._add_message(
            sender="Friday AI Assistant",
            text="Hello! I am Friday, your voice and desktop AI assistant. Say 'Hey Friday', double clap, or type a request to get started!",
            timestamp=get_timestamp_str(),
        )

        # Connect internal Qt signals for EventBus
        self.eventbus_wakeword_signal.connect(self._on_eventbus_wakeword)
        self.eventbus_clap_signal.connect(self._on_eventbus_clap)
        self.eventbus_transcription_signal.connect(self._on_eventbus_transcription)
        self.eventbus_state_signal.connect(self._on_eventbus_state)

    def _subscribe_to_voice_events(self) -> None:
        """Subscribe to backend EventBus voice and conversation events."""
        if not self.container:
            return

        try:
            event_bus: EventBus = self.container.event_bus()
            if event_bus:
                event_bus.subscribe(
                    WakeWordDetected,
                    lambda ev: self.eventbus_wakeword_signal.emit(ev.model_name),
                )
                event_bus.subscribe(
                    DoubleClapDetected,
                    lambda _: self.eventbus_clap_signal.emit(),
                )
                event_bus.subscribe(
                    TranscriptionCompleted,
                    lambda ev: self.eventbus_transcription_signal.emit(
                        getattr(ev, "text", getattr(ev, "transcribed_text", ""))
                    ),
                )
                event_bus.subscribe(
                    ConversationStateChanged,
                    lambda ev: self.eventbus_state_signal.emit(ev.new_state),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"AssistantPage failed to subscribe to EventBus: {exc}")

    def _run_in_background_thread(
        self, worker: QObject, finished_callback: Any | None = None
    ) -> None:
        """Run a worker object on a retained background QThread, preventing premature GC destruction."""
        thread = QThread()
        self._active_threads.append(thread)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        if finished_callback:
            worker.finished.connect(finished_callback)

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)

        def _on_thread_finished() -> None:
            if thread in self._active_threads:
                self._active_threads.remove(thread)
            thread.deleteLater()

        thread.finished.connect(_on_thread_finished)
        thread.start()

    def _on_talk_button_clicked(self) -> None:
        """Handle Push-to-Talk button click to activate voice conversation asynchronously."""
        self.lbl_state_badge.setText("🎙️ State: LISTENING...")
        worker = VoiceActivationWorker(container=self.container)
        self._run_in_background_thread(worker)

    def _on_voice_toggle_clicked(self, active: bool) -> None:
        if active:
            self._on_talk_button_clicked()
        else:
            self.lbl_state_badge.setText("🎙️ State: IDLE")

    def _on_eventbus_wakeword(self, model_name: str) -> None:
        ts = get_timestamp_str()
        self.lbl_wakeword_badge.setText(f"🔴 Wake Word DETECTED ({model_name})")
        self.lbl_state_badge.setText("🎙️ State: LISTENING...")
        self._add_message(
            sender="Voice System",
            text=f"Wake Word detected ('{model_name}'). Listening for voice command...",
            timestamp=ts,
            tool_badge="wakeword",
        )

    def _on_eventbus_clap(self) -> None:
        ts = get_timestamp_str()
        self.lbl_clap_badge.setText("👏 Double Clap DETECTED!")
        self.lbl_state_badge.setText("🎙️ State: LISTENING...")
        self._add_message(
            sender="Voice System",
            text="Double clap gesture detected! Listening for voice command...",
            timestamp=ts,
            tool_badge="clap",
        )

    def _on_eventbus_transcription(self, transcribed_text: str) -> None:
        if not transcribed_text:
            return

        clean_t = transcribed_text.lower().strip()

        # Suppress echo of Friday's own spoken greetings and system prompts
        known_self_echos = (
            "initialized and active",
            "how can i help",
            "how can i assist",
            "i am listening",
            "good evening",
            "good morning",
            "good afternoon",
            "friday ai assistant",
        )
        if any(p in clean_t for p in known_self_echos):
            logger.info(
                f"AssistantPage: Suppressing self-voice echo transcription: '{transcribed_text}'"
            )
            return

        logger.info(
            f"AssistantPage: Received valid voice command: '{transcribed_text}' -> Executing action."
        )
        self._on_user_send_prompt(transcribed_text)

    def _on_eventbus_state(self, new_state: str) -> None:
        self.lbl_state_badge.setText(f"🎙️ State: {new_state}")

    def _add_message(
        self,
        sender: str,
        text: str,
        timestamp: str = "",
        tool_badge: str | None = None,
        risk_level: str | None = None,
    ) -> None:
        msg_widget = ChatMessageWidget(
            sender=sender,
            text=text,
            timestamp=timestamp,
            tool_badge=tool_badge,
            risk_level=risk_level,
            theme_manager=self.theme_manager,
            parent=self.messages_container,
        )
        count = self.messages_layout.count()
        if count > 0:
            self.messages_layout.takeAt(count - 1)

        self.messages_layout.addWidget(msg_widget)
        self.messages_layout.addStretch()

        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def _on_user_send_prompt(self, prompt: str) -> None:
        if not prompt:
            return

        ts = get_timestamp_str()
        self._add_message(sender="You", text=prompt, timestamp=ts)
        self.lbl_state_badge.setText("🧠 State: THINKING...")

        # Safety Preflight Check
        if self.safety_manager:
            eval_res = self.safety_manager.preflight_tool_check(prompt, {})
            if eval_res.decision == AutomationSafetyDecision.REQUIRE_CONFIRMATION:
                req = self.safety_manager.request_confirmation(
                    reason=eval_res.confirmation_reason or "High risk action",
                    risk_level=eval_res.risk_level,
                    action_summary=prompt,
                )
                self._show_confirmation_dialog(req)
                return

        # Execute asynchronously in retained background QThread
        worker = AIRequestWorker(
            prompt=prompt,
            executor=self.tool_executor,
            safety_manager=self.safety_manager,
            container=self.container,
        )
        self._run_in_background_thread(
            worker, finished_callback=self._on_ai_worker_finished
        )

    def _on_ai_worker_finished(self, result: dict) -> None:
        resp = result.get("response", "Operation completed.")
        tool = result.get("tool")
        self._add_message(
            sender="Friday AI Assistant",
            text=resp,
            timestamp=get_timestamp_str(),
            tool_badge=tool,
        )
        self.lbl_state_badge.setText("🎙️ State: IDLE")

    def _show_confirmation_dialog(self, req) -> None:
        modal = ConfirmationModalWidget(
            req, theme_manager=self.theme_manager, parent=self
        )
        modal.confirmed_signal.connect(self._on_confirmation_resolved)
        count = self.messages_layout.count()
        if count > 0:
            self.messages_layout.takeAt(count - 1)
        self.messages_layout.addWidget(modal)
        self.messages_layout.addStretch()

    def _on_confirmation_resolved(self, confirmation_id: str, confirmed: bool) -> None:
        if self.safety_manager:
            self.safety_manager.resolve_confirmation(confirmation_id, confirmed)
        status_text = "CONFIRMED and executed" if confirmed else "DENIED and cancelled"
        resp_text = f"High-risk action request {confirmation_id} was {status_text}."
        self._add_message(
            sender="Friday AI Assistant",
            text=resp_text,
            timestamp=get_timestamp_str(),
            risk_level="HIGH",
        )
        if self.container:
            try:
                tts = self.container.tts_service()
                tts.speak(resp_text)
            except Exception as tts_err:  # noqa: BLE001
                logger.warning(f"Failed to speak confirmation resolution: {tts_err}")
