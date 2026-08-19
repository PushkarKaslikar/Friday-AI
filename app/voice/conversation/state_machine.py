"""Real-time conversation state machine and voice orchestration engine.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
"""

import threading
import time
import uuid
from typing import Any

from app.config.manager import ConfigurationManager
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.voice.clap.events import DoubleClapDetected
from app.voice.conversation.diagnostics import ConversationDiagnostics
from app.voice.conversation.events import (
    BargeInDetected,
    ConversationActivated,
    ConversationEnded,
    ConversationListeningStarted,
    ConversationProcessingStarted,
    ConversationSpeakingCompleted,
    ConversationSpeakingStarted,
    ConversationStateChanged,
)
from app.voice.conversation.metrics import ConversationMetrics
from app.voice.conversation.models import (
    ActivationSource,
    ConversationConfiguration,
    ConversationSession,
    ConversationState,
)
from app.voice.conversation.response_provider_interface import (
    IConversationResponseProvider,
)
from app.voice.conversation.state_machine_interface import IConversationStateMachine
from app.voice.conversation.test_response_provider import TestResponseProvider
from app.voice.stt.events import TranscriptionCompleted, TranscriptionFailed
from app.voice.stt.stt_service import STTService
from app.voice.tts.events import (
    TTSFailed,
    TTSPlaybackCompleted,
    TTSPlaybackStarted,
    TTSStopped,
)
from app.voice.tts.tts_service import TTSService
from app.voice.vad.events import SpeechStarted, SpeechStopped
from app.voice.wakeword.events import WakeWordDetected


class ConversationStateMachine(BaseService, IConversationStateMachine):
    """Deterministic real-time conversation state machine orchestrating voice subsystems."""

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        event_bus: EventBus | None = None,
        stt_service: STTService | None = None,
        tts_service: TTSService | None = None,
        response_provider: IConversationResponseProvider | None = None,
        metrics: ConversationMetrics | None = None,
        diagnostics: ConversationDiagnostics | None = None,
    ) -> None:
        super().__init__(name="ConversationStateMachine", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.event_bus = event_bus or EventBus()
        self.stt_service = stt_service
        self.tts_service = tts_service
        self.response_provider = response_provider or TestResponseProvider()
        self.metrics = metrics or ConversationMetrics()
        self.diagnostics = diagnostics or ConversationDiagnostics(metrics=self.metrics)

        self._conversation_config: ConversationConfiguration = (
            self._load_conversation_configuration()
        )

        self._conversation_state: ConversationState = ConversationState.IDLE
        self._session: ConversationSession | None = None
        self._lock = threading.RLock()
        self._timeout_timer: threading.Timer | None = None
        self._last_error: str | None = None

    @property
    def state(self) -> ConversationState:
        """Current public state of conversation state machine."""
        with self._lock:
            return self._conversation_state

    @property
    def active_session(self) -> ConversationSession | None:
        """Active conversation session metadata."""
        with self._lock:
            return self._session

    @property
    def conversation_config(self) -> ConversationConfiguration:
        """Active configuration model."""
        return self._conversation_config

    @property
    def is_active(self) -> bool:
        """Check if conversation session is currently active (not IDLE)."""
        with self._lock:
            return self._conversation_state != ConversationState.IDLE and self._session is not None

    def _load_conversation_configuration(self) -> ConversationConfiguration:
        """Load conversation settings from ConfigurationManager."""
        try:
            settings = self.config_manager.settings
            if hasattr(settings, "conversation"):
                cfg = settings.conversation
                return ConversationConfiguration(
                    enabled=cfg.enabled,
                    session_timeout_seconds=cfg.session_timeout_seconds,
                    barge_in_enabled=cfg.barge_in_enabled,
                    minimum_barge_in_duration_ms=cfg.minimum_barge_in_duration_ms,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"ConversationStateMachine: Failed to load settings from config, using defaults: {exc}"
            )

        return ConversationConfiguration()

    def _set_state(self, new_state: ConversationState, reason: str = "") -> None:
        """Transition internal state and emit EventBus event."""
        if self._conversation_state != new_state:
            prev = self._conversation_state
            self._conversation_state = new_state

            sess_id = self._session.session_id if self._session else ""
            if self._session:
                self._session.current_state = new_state
                self._session.last_activity = time.time()

            self.metrics.record_state_transition(is_valid=True)
            self.event_bus.publish(
                ConversationStateChanged(
                    previous_state=prev.value,
                    new_state=new_state.value,
                    session_id=sess_id,
                    reason=reason,
                )
            )
            logger.info(
                f"ConversationStateMachine: State transition {prev.value} -> {new_state.value} ({reason})"
            )

    def _reset_timeout_timer(self) -> None:
        """Reset or start idle session timeout timer."""
        self._cancel_timeout_timer()
        if self._conversation_state in (
            ConversationState.LISTENING,
            ConversationState.CONVERSATION_ACTIVE,
        ):
            timeout_sec = self._conversation_config.session_timeout_seconds
            self._timeout_timer = threading.Timer(
                timeout_sec,
                self._on_session_timeout,
            )
            self._timeout_timer.daemon = True
            self._timeout_timer.start()

    def _cancel_timeout_timer(self) -> None:
        """Cancel running session timeout timer."""
        if self._timeout_timer is not None:
            self._timeout_timer.cancel()
            self._timeout_timer = None

    def _on_session_timeout(self) -> None:
        """Callback executed when session timeout timer fires."""
        logger.info("ConversationStateMachine: Session timeout timer expired.")
        self.end_conversation(reason="session_timeout")

    def _do_initialize(self) -> None:
        """Initialize state machine service."""
        logger.info("ConversationStateMachine: Initialized service parameters.")

    def _do_start(self) -> None:
        """Start listening to EventBus events for voice orchestration."""
        self.event_bus.subscribe(DoubleClapDetected, self._on_double_clap)
        self.event_bus.subscribe(WakeWordDetected, self._on_wake_word)
        self.event_bus.subscribe(SpeechStarted, self._on_speech_started)
        self.event_bus.subscribe(SpeechStopped, self._on_speech_stopped)
        self.event_bus.subscribe(
            TranscriptionCompleted, self._on_transcription_completed
        )
        self.event_bus.subscribe(TranscriptionFailed, self._on_transcription_failed)
        self.event_bus.subscribe(TTSPlaybackStarted, self._on_tts_playback_started)
        self.event_bus.subscribe(TTSPlaybackCompleted, self._on_tts_playback_completed)
        self.event_bus.subscribe(TTSStopped, self._on_tts_stopped)
        self.event_bus.subscribe(TTSFailed, self._on_tts_failed)
        logger.info(
            "ConversationStateMachine: Subscribed to all voice subsystem EventBus events."
        )

    def _do_stop(self) -> None:
        """Stop service and end active session."""
        self.end_conversation(reason="service_stopped")
        logger.info("ConversationStateMachine: Stopped service.")

    def activate(
        self, source: ActivationSource | str = ActivationSource.WAKE_WORD
    ) -> ConversationSession:
        """Activate conversation session from trigger event."""
        if isinstance(source, str):
            try:
                source = ActivationSource(source)
            except ValueError:
                source = ActivationSource.WAKE_WORD

        with self._lock:
            if not self._conversation_config.enabled:
                logger.warning(
                    "ConversationStateMachine: Activation rejected because subsystem is disabled."
                )
                return ConversationSession()

            source_enum = (
                source
                if isinstance(source, ActivationSource)
                else ActivationSource.WAKE_WORD
            )
            source_str = source_enum.value

            # Activation Deduplication: Ignore if already active
            if self._conversation_state != ConversationState.IDLE and self._session is not None:
                logger.info(
                    f"ConversationStateMachine: Duplicate activation trigger '{source_str}' "
                    f"ignored in state '{self._conversation_state.value}'."
                )
                return self._session

            sess_id = str(uuid.uuid4())
            session = ConversationSession(
                session_id=sess_id,
                activation_source=source_enum,
                current_state=ConversationState.AWAKENING,
                turn_count=1,
            )
            self._session = session
            self.metrics.record_activation(source_enum)

            self.event_bus.publish(
                ConversationActivated(session_id=sess_id, activation_source=source_str)
            )

            # Transition IDLE -> AWAKENING -> LISTENING
            self._set_state(
                ConversationState.AWAKENING, reason=f"Activated by {source_str}"
            )
            self._set_state(ConversationState.LISTENING, reason="Activation ready")

            self.event_bus.publish(
                ConversationListeningStarted(session_id=sess_id, turn_count=1)
            )
            self._reset_timeout_timer()
            return session

    def provide_response(self, text: str) -> None:
        """Provide response text for TTS synthesis."""
        with self._lock:
            if self._conversation_state != ConversationState.PROCESSING or not self._session:
                logger.warning(
                    f"ConversationStateMachine: provide_response ignored in state '{self._conversation_state.value}'."
                )
                return

            clean_text = text.strip()
            if not clean_text:
                self._set_state(
                    ConversationState.CONVERSATION_ACTIVE, reason="Empty response text"
                )
                self._reset_timeout_timer()
                return

            sess_id = self._session.session_id
            turn = self._session.turn_count

            self._set_state(ConversationState.SPEAKING, reason="Response ready for TTS")
            self.event_bus.publish(
                ConversationSpeakingStarted(
                    session_id=sess_id, text=clean_text, turn_count=turn
                )
            )

            if self.tts_service:
                # Dispatch speak request asynchronously to prevent blocking callback
                threading.Thread(
                    target=self.tts_service.speak,
                    args=(clean_text, True),
                    daemon=True,
                ).start()

    def stop_speaking(self) -> None:
        """Stop TTS speaking playback and execute barge-in transition to LISTENING."""
        with self._lock:
            if self._conversation_state != ConversationState.SPEAKING or not self._session:
                return

            sess_id = self._session.session_id
            turn = self._session.turn_count

            self.metrics.record_barge_in()
            self.event_bus.publish(BargeInDetected(session_id=sess_id, turn_count=turn))

            if self.tts_service:
                self.tts_service.stop()

            self._set_state(
                ConversationState.LISTENING, reason="Barge-in user speech detected"
            )
            self.event_bus.publish(
                ConversationListeningStarted(session_id=sess_id, turn_count=turn)
            )
            self._reset_timeout_timer()

    def end_conversation(self, reason: str = "user_requested") -> None:
        """End current conversation session and return to IDLE."""
        with self._lock:
            self._cancel_timeout_timer()
            if self._session:
                sess_id = self._session.session_id
                duration = round(time.time() - self._session.created_at, 2)
                turns = self._session.turn_count

                self.metrics.record_session_end(reason, duration)
                self.event_bus.publish(
                    ConversationEnded(
                        session_id=sess_id,
                        reason=reason,
                        turn_count=turns,
                        duration_seconds=duration,
                    )
                )
                self._session = None

            self._set_state(ConversationState.IDLE, reason=reason)

    # --- EventBus Event Handler Callbacks ---

    def _on_double_clap(self, evt: DoubleClapDetected) -> None:
        """Event handler for double clap activation."""
        self.activate(ActivationSource.DOUBLE_CLAP)

    def _on_wake_word(self, evt: WakeWordDetected) -> None:
        """Event handler for wake word activation."""
        self.activate(ActivationSource.WAKE_WORD)

    def _on_speech_started(self, evt: SpeechStarted) -> None:
        """Event handler when user starts speaking."""
        with self._lock:
            if self._conversation_state == ConversationState.SPEAKING:
                # User Barge-In Interruption
                if self._conversation_config.barge_in_enabled:
                    logger.info(
                        "ConversationStateMachine: Barge-in detected during SPEAKING state."
                    )
                    self.stop_speaking()
            elif self._conversation_state in (
                ConversationState.LISTENING,
                ConversationState.CONVERSATION_ACTIVE,
            ):
                if self._conversation_state == ConversationState.CONVERSATION_ACTIVE:
                    if self._session:
                        self._session.turn_count += 1
                    self._set_state(
                        ConversationState.LISTENING, reason="User started speaking turn"
                    )
                self._reset_timeout_timer()

    def _on_speech_stopped(self, evt: SpeechStopped) -> None:
        """Event handler when user stops speaking."""
        with self._lock:
            if self._conversation_state == ConversationState.LISTENING and self._session:
                self._cancel_timeout_timer()
                sess_id = self._session.session_id
                turn = self._session.turn_count

                self._set_state(
                    ConversationState.PROCESSING, reason="User speech finished"
                )
                self.event_bus.publish(
                    ConversationProcessingStarted(session_id=sess_id, turn_count=turn)
                )

    def _on_transcription_completed(self, evt: TranscriptionCompleted) -> None:
        """Event handler when STT finishes transcription."""
        with self._lock:
            if self._conversation_state != ConversationState.PROCESSING or not self._session:
                return

            transcript = evt.text.strip()
            if not transcript:
                logger.info("ConversationStateMachine: Empty STT transcript received.")
                self._set_state(
                    ConversationState.CONVERSATION_ACTIVE, reason="Empty STT transcript"
                )
                self._reset_timeout_timer()
                return

            sess_id = self._session.session_id
            response_text = self.response_provider.get_response(
                transcript, session_id=sess_id
            )

            turn = self._session.turn_count
            self._set_state(
                ConversationState.SPEAKING, reason="STT transcription complete"
            )
            self.event_bus.publish(
                ConversationSpeakingStarted(
                    session_id=sess_id, text=response_text, turn_count=turn
                )
            )

            if self.tts_service:
                threading.Thread(
                    target=self.tts_service.speak,
                    args=(response_text, True),
                    daemon=True,
                ).start()

    def _on_transcription_failed(self, evt: TranscriptionFailed) -> None:
        """Event handler when STT transcription fails."""
        with self._lock:
            if self._conversation_state == ConversationState.PROCESSING:
                self.metrics.record_error("stt")
                logger.warning(
                    "ConversationStateMachine: STT transcription failed, returning to LISTENING."
                )
                self._set_state(ConversationState.LISTENING, reason="STT failed")
                self._reset_timeout_timer()

    def _on_tts_playback_started(self, evt: TTSPlaybackStarted) -> None:
        """Event handler when TTS playback starts."""

    def _on_tts_playback_completed(self, evt: TTSPlaybackCompleted) -> None:
        """Event handler when TTS playback completes successfully (with stale event protection)."""
        with self._lock:
            # Stale Event Protection: Ignore if state is no longer SPEAKING
            if self._conversation_state != ConversationState.SPEAKING or not self._session:
                logger.debug(
                    "ConversationStateMachine: Stale TTSPlaybackCompleted event ignored."
                )
                return

            sess_id = self._session.session_id
            turn = self._session.turn_count
            self.metrics.record_turn()

            self.event_bus.publish(
                ConversationSpeakingCompleted(
                    session_id=sess_id, text=evt.text, turn_count=turn
                )
            )

            self._set_state(
                ConversationState.CONVERSATION_ACTIVE, reason="TTS playback completed"
            )
            self._reset_timeout_timer()

    def _on_tts_stopped(self, evt: TTSStopped) -> None:
        """Event handler when TTS playback is stopped."""

    def _on_tts_failed(self, evt: TTSFailed) -> None:
        """Event handler when TTS playback fails."""
        with self._lock:
            if self._conversation_state == ConversationState.SPEAKING:
                self.metrics.record_error("tts")
                logger.warning(
                    "ConversationStateMachine: TTS failed, transitioning to CONVERSATION_ACTIVE."
                )
                self._set_state(
                    ConversationState.CONVERSATION_ACTIVE, reason="TTS failed"
                )
                self._reset_timeout_timer()

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        with self._lock:
            cur_state = self._conversation_state.value
            active = self._session is not None and self._conversation_state != ConversationState.IDLE
            sess_id = self._session.session_id if self._session else None
            source = self._session.activation_source.value if self._session else None
            turns = self._session.turn_count if self._session else 0

        return self.diagnostics.get_health_report(
            service_state="RUNNING" if self.is_running else "STOPPED",
            current_state=cur_state,
            session_active=active,
            session_id=sess_id,
            activation_source=source,
            turn_count=turns,
            barge_in_enabled=self._conversation_config.barge_in_enabled,
            session_timeout_seconds=self._conversation_config.session_timeout_seconds,
            enabled=self._conversation_config.enabled,
            last_error=self._last_error,
        )

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor service integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
