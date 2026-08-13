"""Comprehensive test suite for Text-to-Speech (TTS) Subsystem.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

from typing import Any

import numpy as np
import pytest

from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.services.events.event_bus import EventBus
from app.voice.audio.audio_engine import AudioEngine
from app.voice.clap.clap_detector import ClapDetector
from app.voice.stt.stt_service import STTService
from app.voice.tts.audio_adapter import TTSAudioAdapter
from app.voice.tts.events import (
    TTSPlaybackCompleted,
    TTSPlaybackStarted,
    TTSStopped,
    TTSSynthesisCompleted,
    TTSSynthesisStarted,
)
from app.voice.tts.models import TTSConfiguration, TTSResult
from app.voice.tts.piper_tts_provider import PiperTTSProvider
from app.voice.tts.tts_provider_interface import ITTSProvider
from app.voice.tts.tts_service import TTSService
from app.voice.vad.vad_detector import VADDetector
from app.voice.wakeword.wakeword_detector import WakeWordDetector


class FakeTTSProvider(ITTSProvider):
    """Deterministic fake TTS model provider for fast unit tests."""

    def __init__(self, sample_rate: int = 22050) -> None:
        self._sample_rate = sample_rate
        self._loaded = True

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def load_model(self) -> bool:
        self._loaded = True
        return True

    def synthesize(self, text: str) -> tuple[np.ndarray, int, TTSResult]:
        clean_text = text.strip()
        if not clean_text:
            return (
                np.zeros(0, dtype=np.float32),
                self._sample_rate,
                TTSResult(text="", status="EMPTY_INPUT"),
            )

        # Produce 1.0s synthetic 440Hz sine wave audio
        t = np.linspace(0, 1.0, int(self._sample_rate * 1.0), endpoint=False)
        audio = (0.2 * np.sin(2 * np.pi * 440.0 * t)).astype(np.float32)

        res = TTSResult(
            text=clean_text,
            audio_duration_seconds=1.0,
            synthesis_time_seconds=0.05,
            real_time_factor=0.05,
            voice_name="en_US-amy-medium",
            sample_rate=self._sample_rate,
            status="SUCCESS",
        )
        return audio, self._sample_rate, res

    def unload_model(self) -> None:
        self._loaded = False


def test_tts_configuration():
    """Verify default TTSConfiguration models."""
    cfg = TTSConfiguration()
    assert cfg.enabled is True
    assert cfg.voice == "en_US-amy-medium"
    assert cfg.language == "en_US"
    assert cfg.max_text_length == 500
    assert cfg.auto_play is True


def test_tts_text_validation_and_chunking():
    """Verify text validation and sentence chunking logic."""
    fake_provider = FakeTTSProvider()
    service = TTSService(provider=fake_provider)

    # Empty text handling
    empty_res = service.speak("   ")
    assert empty_res.status == "EMPTY_INPUT"

    # Sentence chunking test
    long_text = "Sentence one. " * 50  # > 500 chars
    chunks = service._split_into_chunks(long_text)
    assert len(chunks) > 1
    assert all(len(c) <= 500 for c in chunks)


def test_tts_audio_adapter_resampling():
    """Verify sample rate conversion (22050 Hz to 16000 Hz)."""
    samples = np.zeros(22050, dtype=np.float32)
    resampled = TTSAudioAdapter.prepare_audio(
        audio_samples=samples,
        source_sample_rate=22050,
        target_sample_rate=16000,
    )
    assert isinstance(resampled, np.ndarray)
    assert resampled.dtype == np.float32
    assert len(resampled) == 16000


def test_tts_service_speak_and_events():
    """Verify TTSService speak(), synthesize(), and EventBus event publications."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    audio_engine = AudioEngine(config_manager=config_mgr, event_bus=event_bus)
    audio_engine.initialize()

    fake_provider = FakeTTSProvider()
    service = TTSService(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        provider=fake_provider,
    )
    service.initialize()
    service.start()

    events_received: list[Any] = []

    def on_event(evt: Any):
        events_received.append(evt)

    event_bus.subscribe(TTSSynthesisStarted, on_event)
    event_bus.subscribe(TTSSynthesisCompleted, on_event)
    event_bus.subscribe(TTSPlaybackStarted, on_event)
    event_bus.subscribe(TTSPlaybackCompleted, on_event)

    result = service.speak("Hello Pushkar. Friday is ready.")

    assert result.status == "SUCCESS"
    assert result.audio_duration_seconds == 1.0
    assert len(events_received) == 4

    types = [type(e) for e in events_received]
    assert TTSSynthesisStarted in types
    assert TTSSynthesisCompleted in types
    assert TTSPlaybackStarted in types
    assert TTSPlaybackCompleted in types

    report = service.get_health_report()
    assert report["status"] == "HEALTHY"
    assert report["model_loaded"] is True
    assert report["metrics"]["successful_synthesis"] == 1

    service.stop()
    audio_engine.stop()


def test_tts_service_stop_bargein():
    """Verify TTSService stop() flushes pending playback queue."""
    event_bus = EventBus()
    config_mgr = ConfigurationManager()
    audio_engine = AudioEngine(config_manager=config_mgr, event_bus=event_bus)
    audio_engine.initialize()

    fake_provider = FakeTTSProvider()
    service = TTSService(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        provider=fake_provider,
    )
    service.initialize()

    stopped_events = []
    event_bus.subscribe(TTSStopped, lambda e: stopped_events.append(e))

    # Enqueue dummy audio into audio engine output
    audio_engine.play(np.zeros(16000, dtype=np.float32))
    assert audio_engine.output_stream.is_playing is True

    service.stop()

    assert audio_engine.output_stream.is_playing is False
    assert len(stopped_events) == 1
    assert stopped_events[0].reason == "User requested stop"

    service.stop()
    audio_engine.stop()


def test_tts_bootstrapper_integration(qapp):
    """Verify TTSService integration into 8-step AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        container = result.container
        tts_service: TTSService = container.tts_service()

        assert tts_service is not None
        report = tts_service.get_health_report()
        assert report["provider"] == "Piper (piper-tts)"
        assert "metrics" in report
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()


def test_five_way_audio_coexistence():
    """Verify ClapDetector, WakeWordDetector, VADDetector, STTService, and TTSService coexist on AudioEngine."""
    config_mgr = ConfigurationManager()
    event_bus = EventBus()
    audio_engine = AudioEngine(config_manager=config_mgr, event_bus=event_bus)
    audio_engine.initialize()

    clap_detector = ClapDetector(
        config_manager=config_mgr, audio_engine=audio_engine, event_bus=event_bus
    )
    ww_detector = WakeWordDetector(
        config_manager=config_mgr, audio_engine=audio_engine, event_bus=event_bus
    )
    vad_detector = VADDetector(
        config_manager=config_mgr, audio_engine=audio_engine, event_bus=event_bus
    )
    stt_service = STTService(
        config_manager=config_mgr, audio_engine=audio_engine, event_bus=event_bus
    )
    tts_service = TTSService(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        provider=FakeTTSProvider(),
    )

    clap_detector.initialize()
    ww_detector.initialize()
    vad_detector.initialize()
    stt_service.initialize()
    tts_service.initialize()

    # Confirm 3 frame input subscribers + TTS provider
    assert len(audio_engine.input_stream._subscribers) == 3
    assert tts_service.provider.is_loaded is True

    # Test synthesizing speech audio while input stream callbacks receive frames
    dummy_input = np.zeros((512, 1), dtype=np.float32)
    audio_engine.input_stream._audio_callback(dummy_input, 512, None, None)

    res = tts_service.speak("Five-way voice coexistence test complete.")
    assert res.status == "SUCCESS"

    tts_service.stop()
    stt_service.stop()
    vad_detector.stop()
    ww_detector.stop()
    clap_detector.stop()
    audio_engine.stop()


def test_real_piper_tts_provider():
    """Integration test executing real PiperTTSProvider with downloaded female voice model."""
    provider = PiperTTSProvider(config=TTSConfiguration(voice="en_US-amy-medium"))
    loaded = provider.load_model()
    if not loaded:
        pytest.skip("PiperTTSProvider voice model unavailable.")

    assert provider.is_loaded is True
    assert provider.sample_rate == 22050

    audio, sr, res = provider.synthesize(
        "Hello Pushkar. Testing local Piper female voice."
    )
    assert res.status == "SUCCESS"
    assert len(audio) > 0
    assert sr == 22050
    assert res.audio_duration_seconds > 0.5
    assert res.real_time_factor < 0.30

    provider.unload_model()
    assert provider.is_loaded is False
