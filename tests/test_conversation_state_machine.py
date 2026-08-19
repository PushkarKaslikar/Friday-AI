"""Comprehensive test suite for Conversation State Machine & Voice Orchestration.

Phase 3.7 - Conversation State Machine & Real-Time Voice Orchestration
"""

import time

import numpy as np

from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.services.events.event_bus import EventBus
from app.voice.audio.audio_engine import AudioEngine
from app.voice.clap.events import DoubleClapDetected
from app.voice.conversation.events import (
    BargeInDetected,
    ConversationActivated,
    ConversationStateChanged,
)
from app.voice.conversation.models import (
    ActivationSource,
    ConversationConfiguration,
    ConversationState,
)
from app.voice.conversation.state_machine import ConversationStateMachine
from app.voice.conversation.test_response_provider import TestResponseProvider
from app.voice.stt.events import TranscriptionCompleted
from app.voice.tts.events import TTSPlaybackCompleted
from app.voice.tts.models import TTSResult
from app.voice.tts.tts_provider_interface import ITTSProvider
from app.voice.tts.tts_service import TTSService
from app.voice.vad.events import SpeechStarted, SpeechStopped
from app.voice.wakeword.events import WakeWordDetected


class MockTTSProvider(ITTSProvider):
    """Deterministic mock TTS provider for testing state machine orchestration."""

    def __init__(self) -> None:
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def sample_rate(self) -> int:
        return 22050

    def load_model(self) -> bool:
        self._loaded = True
        return True

    def synthesize(self, text: str) -> tuple[np.ndarray, int, TTSResult]:
        samples = np.zeros(1600, dtype=np.float32)
        res = TTSResult(text=text, audio_duration_seconds=0.1, status="SUCCESS")
        return samples, 22050, res

    def unload_model(self) -> None:
        self._loaded = False


def test_conversation_configuration():
    """Verify default ConversationConfiguration settings."""
    cfg = ConversationConfiguration()
    assert cfg.enabled is True
    assert cfg.session_timeout_seconds == 10.0
    assert cfg.barge_in_enabled is True
    assert cfg.minimum_barge_in_duration_ms == 100.0


def test_conversation_activation_clap_and_wakeword():
    """Verify state transitions from DoubleClapDetected and WakeWordDetected triggers."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    state_machine = ConversationStateMachine(
        config_manager=config_mgr,
        event_bus=event_bus,
        response_provider=TestResponseProvider(),
    )
    state_machine.initialize()
    state_machine.start()

    activated_events = []
    event_bus.subscribe(ConversationActivated, lambda e: activated_events.append(e))

    # Trigger DoubleClap activation
    event_bus.publish(DoubleClapDetected(confidence=0.95))
    assert state_machine.state == ConversationState.LISTENING
    assert state_machine.is_active is True
    assert (
        state_machine.active_session.activation_source == ActivationSource.DOUBLE_CLAP
    )
    assert len(activated_events) == 1

    # End session
    state_machine.end_conversation(reason="test_reset")
    assert state_machine.state == ConversationState.IDLE
    assert state_machine.is_active is False

    # Trigger WakeWord activation
    event_bus.publish(WakeWordDetected(wake_word="friday", score=0.92))
    assert state_machine.state == ConversationState.LISTENING
    assert state_machine.active_session.activation_source == ActivationSource.WAKE_WORD
    assert len(activated_events) == 2

    state_machine.stop()


def test_activation_deduplication():
    """Verify duplicate activation events while already active are safely ignored."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    state_machine = ConversationStateMachine(
        config_manager=config_mgr,
        event_bus=event_bus,
    )
    state_machine.initialize()
    state_machine.start()

    sess1 = state_machine.activate(ActivationSource.WAKE_WORD)
    assert state_machine.state == ConversationState.LISTENING

    # Duplicate activation attempt while active
    sess2 = state_machine.activate(ActivationSource.DOUBLE_CLAP)
    assert sess2.session_id == sess1.session_id
    assert state_machine.state == ConversationState.LISTENING
    assert state_machine.metrics.get_metrics_snapshot()["activations_total"] == 1

    state_machine.stop()


def test_conversation_full_turn_lifecycle():
    """Verify full multi-turn conversational turn flow."""
    from unittest.mock import MagicMock

    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    audio_engine = MagicMock(spec=AudioEngine)

    tts_service = TTSService(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        provider=MockTTSProvider(),
    )
    tts_service.initialize()

    state_machine = ConversationStateMachine(
        config_manager=config_mgr,
        event_bus=event_bus,
        tts_service=tts_service,
        response_provider=TestResponseProvider(),
    )
    state_machine.initialize()
    state_machine.start()

    transitions: list[str] = []
    event_bus.subscribe(
        ConversationStateChanged,
        lambda e: transitions.append(f"{e.previous_state}->{e.new_state}"),
    )

    # 1. Activate
    event_bus.publish(WakeWordDetected(wake_word="friday"))
    assert state_machine.state == ConversationState.LISTENING

    # 2. User Speech Boundary (VAD)
    event_bus.publish(SpeechStarted())
    event_bus.publish(SpeechStopped(speech_duration=1.5))
    assert state_machine.state == ConversationState.PROCESSING

    # 3. STT Transcription
    event_bus.publish(TranscriptionCompleted(text="Hello Friday", language="en"))
    assert state_machine.state == ConversationState.SPEAKING

    # 4. TTS Playback Complete
    event_bus.publish(
        TTSPlaybackCompleted(text="Hello Pushkar", audio_duration_seconds=1.0)
    )
    assert state_machine.state == ConversationState.CONVERSATION_ACTIVE
    assert state_machine.active_session.turn_count == 1

    # 5. Turn 2: User speaks again in CONVERSATION_ACTIVE
    event_bus.publish(SpeechStarted())
    assert state_machine.state == ConversationState.LISTENING
    assert state_machine.active_session.turn_count == 2

    state_machine.stop()
    tts_service.stop()


def test_barge_in_orchestration():
    """Verify user speech during SPEAKING triggers TTSService.stop() and transitions to LISTENING."""
    from unittest.mock import MagicMock

    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    audio_engine = MagicMock(spec=AudioEngine)

    tts_service = TTSService(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        provider=MockTTSProvider(),
    )
    tts_service.initialize()

    state_machine = ConversationStateMachine(
        config_manager=config_mgr,
        event_bus=event_bus,
        tts_service=tts_service,
    )
    state_machine.initialize()
    state_machine.start()

    barge_in_events = []
    event_bus.subscribe(BargeInDetected, lambda e: barge_in_events.append(e))

    state_machine.activate(ActivationSource.WAKE_WORD)
    event_bus.publish(SpeechStopped())
    event_bus.publish(TranscriptionCompleted(text="Long question"))

    assert state_machine.state == ConversationState.SPEAKING

    # User speaks while Friday is speaking (Barge-In)
    event_bus.publish(SpeechStarted())

    assert len(barge_in_events) == 1
    assert state_machine.state == ConversationState.LISTENING
    assert state_machine.metrics.get_metrics_snapshot()["barge_ins"] == 1

    state_machine.stop()
    tts_service.stop()


def test_stale_event_protection():
    """Verify stale TTSPlaybackCompleted events after barge-in do not corrupt state."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    state_machine = ConversationStateMachine(
        config_manager=config_mgr,
        event_bus=event_bus,
    )
    state_machine.initialize()
    state_machine.start()

    state_machine.activate(ActivationSource.WAKE_WORD)
    event_bus.publish(SpeechStopped())
    event_bus.publish(TranscriptionCompleted(text="Hello"))

    assert state_machine.state == ConversationState.SPEAKING

    # User interrupts (Barge-In) -> LISTENING
    state_machine.stop_speaking()
    assert state_machine.state == ConversationState.LISTENING

    # Stale TTS playback event arrives from old synthesis job
    event_bus.publish(TTSPlaybackCompleted(text="Hello", audio_duration_seconds=1.0))

    # State MUST remain LISTENING, not transition to CONVERSATION_ACTIVE
    assert state_machine.state == ConversationState.LISTENING

    state_machine.stop()


def test_session_timeout():
    """Verify idle conversation session automatically times out to IDLE."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    state_machine = ConversationStateMachine(
        config_manager=config_mgr,
        event_bus=event_bus,
    )
    # Set short timeout for test
    state_machine._conversation_config.session_timeout_seconds = 0.2
    state_machine.initialize()
    state_machine.start()

    state_machine.activate(ActivationSource.WAKE_WORD)
    assert state_machine.state == ConversationState.LISTENING

    time.sleep(0.35)

    assert state_machine.state == ConversationState.IDLE
    assert state_machine.is_active is False
    assert state_machine.metrics.get_metrics_snapshot()["sessions_timed_out"] == 1

    state_machine.stop()


def test_conversation_bootstrapper_integration(qapp):
    """Verify ConversationStateMachine integration into 8-step AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        container = result.container
        c_sm: ConversationStateMachine = container.conversation_state_machine()

        assert c_sm is not None
        report = c_sm.get_health_report()
        assert report["provider"] == "ConversationStateMachine (Deterministic)"
        assert report["current_state"] == "IDLE"
        assert "metrics" in report
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()


def test_six_way_voice_coexistence(qapp):
    """Verify all voice services (AudioEngine, Clap, WakeWord, VAD, STT, TTS, StateMachine) coexist cleanly."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        c_sm: ConversationStateMachine = result.container.conversation_state_machine()
        audio_engine = result.container.audio_engine()
        event_bus = result.container.event_bus()

        assert c_sm.is_running is True
        assert audio_engine.state.value in ("READY", "RUNNING")
        assert len(audio_engine.input_stream._subscribers) >= 3

        # Simulate DoubleClap activation
        event_bus.publish(DoubleClapDetected(confidence=0.95))
        assert c_sm.state == ConversationState.LISTENING

        # Simulate turn
        event_bus.publish(SpeechStarted())
        event_bus.publish(SpeechStopped())
        assert c_sm.state == ConversationState.PROCESSING

        event_bus.publish(
            TranscriptionCompleted(text="Test six-way coexistence")
        )
        assert c_sm.state == ConversationState.SPEAKING

        c_sm.end_conversation(reason="test_complete")
        assert c_sm.state == ConversationState.IDLE
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()
