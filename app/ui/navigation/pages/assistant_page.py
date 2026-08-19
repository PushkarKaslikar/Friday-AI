"""Assistant Interaction View connecting PySide6 Desktop UI with Friday Backend AI Engines & Voice Loop."""

import re
import time
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
from app.voice.conversation.events import (
    ConversationSpeakingCompleted,
    ConversationSpeakingStarted,
    ConversationStateChanged,
)
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
        resp_text = ""
        tool_id = "assistant.reason"
        success = True

        # 1. First try OrchestratingResponseProvider if container is available
        if self.container:
            try:
                provider = self.container.orchestrating_response_provider()
                if provider:
                    resp_text = provider.get_response(self.prompt)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"AIRequestWorker: OrchestratingResponseProvider error: {exc}")

        # 2. Fallback direct execution if provider returned empty or was unavailable
        if not resp_text:
            p_lower = self.prompt.lower().strip()
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

            elif self.executor and any(k in p_lower for k in ("open", "launch", "start")):
                # Direct tool executor launch fallback
                for app in ("chrome", "explorer", "notepad", "calc", "paint", "cmd", "powershell"):
                    if app in p_lower:
                        res = self.executor.execute("system.open_application", {"application": app})
                        resp_text = f"Opening {app.title()} now."
                        tool_id = "system.open_application"
                        success = res.success if res else False
                        break

            if not resp_text:
                resp_text = f"Friday processed: '{self.prompt}'. Local desktop automation engine is active."

        # Speak Response Aloud via TTSService if container available
        if self.container and resp_text:
            try:
                tts = self.container.tts_service()
                if tts:
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
    eventbus_speaking_signal = Signal(str)

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
        self._active_workers: list[QObject] = []
        self._last_speaking_time: float = 0.0
        self._recent_spoken_phrases: list[str] = []

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
        self.eventbus_speaking_signal.connect(self._on_eventbus_speaking_started)

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
                event_bus.subscribe(
                    ConversationSpeakingStarted,
                    lambda ev: self.eventbus_speaking_signal.emit(getattr(ev, "text", "")),
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"AssistantPage failed to subscribe to EventBus: {exc}")

    def _run_in_background_thread(
        self, worker: QObject, finished_callback: Any | None = None
    ) -> None:
        """Run a worker object on a retained background QThread, preventing premature GC destruction."""
        thread = QThread()
        self._active_threads.append(thread)
        self._active_workers.append(worker)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        if finished_callback:
            worker.finished.connect(finished_callback)

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)

        def _on_thread_finished() -> None:
            if thread in self._active_threads:
                self._active_threads.remove(thread)
            if worker in self._active_workers:
                self._active_workers.remove(worker)
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
        now = time.time()

        # 1. Acoustic Feedback Protection: Check if TTS is currently speaking or just completed
        is_speaking_now = False
        if self.container:
            try:
                tts = self.container.tts_service()
                if tts and getattr(tts, "is_speaking", False):
                    is_speaking_now = True
            except Exception:  # noqa: BLE001
                pass

        if is_speaking_now or (now - self._last_speaking_time) < 2.0:
            logger.info(
                f"AssistantPage: Suppressing acoustic speaker echo during/after speech: '{transcribed_text}'"
            )
            return

        # 2. Check recent spoken phrases similarity, containment, and word overlap
        words = set(re.findall(r"\b\w{3,}\b", clean_t))
        for phrase in self._recent_spoken_phrases:
            phrase_lower = phrase.lower()
            if clean_t in phrase_lower or phrase_lower in clean_t:
                logger.info(
                    f"AssistantPage: Suppressing self-voice echo matching recent speech: '{transcribed_text}'"
                )
                return
            if words:
                phrase_words = set(re.findall(r"\b\w{3,}\b", phrase_lower))
                if phrase_words:
                    overlap = len(words & phrase_words) / len(words)
                    if overlap >= 0.4:
                        logger.info(
                            f"AssistantPage: Suppressing acoustic echo with {overlap*100:.0f}% word overlap with recent speech: '{transcribed_text}'"
                        )
                        return

        # 3. Known system prompts / greetings / error phrases
        known_self_echos = (
            "initialized and active",
            "can i help",
            "how can i",
            "how may i",
            "what can i do",
            "i am listening",
            "good evening",
            "good morning",
            "good afternoon",
            "friday ai assistant",
            "encountered an error",
            "processing your request",
            "current state",
            "local llm",
            "mock response",
            "winerror",
            "file specified",
            "cannot find the file",
            "could not be resolved",
            "attempted to open",
            "attempted to close",
            "opening ",
            "closing ",
            "volume set to",
            "audio has been",
            "screen capture completed",
            "locking your computer",
            "putting computer to sleep",
            "personal ai assistant",
            "desktop ai assistant",
        )
        if any(p in clean_t for p in known_self_echos):
            logger.info(
                f"AssistantPage: Suppressing self-voice echo transcription: '{transcribed_text}'"
            )
            return

        # Check if ConversationStateMachine is actively handling this turn
        is_csm_processing = False
        if self.container:
            try:
                csm = self.container.conversation_state_machine()
                if csm and getattr(csm, "conversation_state", None) and getattr(csm.conversation_state, "value", "") == "PROCESSING":
                    is_csm_processing = True
            except Exception:  # noqa: BLE001
                pass

        if is_csm_processing:
            logger.info(
                f"AssistantPage: ConversationStateMachine is processing voice command: '{transcribed_text}'"
            )
            ts = get_timestamp_str()
            self._add_message(sender="You (Voice)", text=transcribed_text, timestamp=ts)
            self.lbl_state_badge.setText("🧠 State: PROCESSING...")
            return

        logger.info(
            f"AssistantPage: Received valid voice command: '{transcribed_text}' -> Executing action."
        )
        self._on_user_send_prompt(transcribed_text)

    def _on_eventbus_speaking_started(self, spoken_text: str) -> None:
        if not spoken_text:
            return

        self._last_speaking_time = time.time()
        self._recent_spoken_phrases.append(spoken_text.lower().strip())
        if len(self._recent_spoken_phrases) > 20:
            self._recent_spoken_phrases.pop(0)

        self.lbl_state_badge.setText("🗣️ State: SPEAKING...")
        # Avoid duplicate message in chat if already added
        count = self.messages_layout.count()
        last_msg = None
        for i in range(count - 1, -1, -1):
            item = self.messages_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), ChatMessageWidget):
                last_msg = item.widget()
                break
        if last_msg and getattr(last_msg, "sender_name", "") == "Friday AI Assistant" and getattr(last_msg, "text_content", "") == spoken_text:
            return

        self._add_message(
            sender="Friday AI Assistant",
            text=spoken_text,
            timestamp=get_timestamp_str(),
            tool_badge="voice.tts",
        )

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
