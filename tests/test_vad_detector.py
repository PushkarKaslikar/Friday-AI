"""Unit and integration test suite for Voice Activity Detection (VAD) Subsystem.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

import time
from typing import Any

import numpy as np

from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.services.events.event_bus import EventBus
from app.voice.audio.audio_engine import AudioEngine
from app.voice.audio.models import AudioFrame
from app.voice.clap.clap_detector import ClapDetector
from app.voice.vad.audio_adapter import VADAudioAdapter
from app.voice.vad.events import SpeechStarted, SpeechStopped
from app.voice.vad.models import VADConfiguration, VADState
from app.voice.vad.silero_vad_model import SileroVADModel
from app.voice.vad.state_machine import VADStateMachine
from app.voice.vad.vad_detector import VADDetector
from app.voice.vad.vad_model_interface import IVADModel
from app.voice.wakeword.wakeword_detector import WakeWordDetector


class MockVADModel(IVADModel):
    """Mock VAD model returning pre-scripted speech probabilities."""

    def __init__(self, probabilities: list[float] | None = None) -> None:
        self.probabilities = probabilities or [0.0]
        self.call_count = 0
        self._loaded = True

    def load_model(self) -> bool:
        self._loaded = True
        return True

    def process_audio(self, audio_samples: Any) -> float:
        if not self.probabilities:
            return 0.0
        idx = min(self.call_count, len(self.probabilities) - 1)
        prob = self.probabilities[idx]
        self.call_count += 1
        return prob

    def reset_state(self) -> None:
        self.call_count = 0

    def unload_model(self) -> None:
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded


def test_vad_configuration_defaults():
    """Verify default VADConfiguration parameters."""
    cfg = VADConfiguration()
    assert cfg.enabled is True
    assert cfg.model_name == "silero_vad"
    assert cfg.speech_threshold == 0.50
    assert cfg.negative_threshold == 0.35
    assert cfg.speech_start_confirmation_ms == 64.0
    assert cfg.min_silence_duration_ms == 300.0
    assert cfg.speech_pad_ms == 64.0
    assert cfg.sample_rate == 16000


def test_silero_vad_model_path_resolution_and_lifecycle():
    """Verify SileroVADModel model loading and ONNX runtime inference execution."""
    model = SileroVADModel()
    loaded = model.load_model()
    assert loaded is True
    assert model.is_loaded is True
    assert "silero_vad.onnx" in model.model_path

    dummy_audio = np.zeros((1, 512), dtype=np.float32)
    prob = model.process_audio(dummy_audio)
    assert 0.0 <= prob <= 1.0

    model.unload_model()
    assert model.is_loaded is False


def test_vad_audio_adapter_formatting():
    """Verify VADAudioAdapter converts float32 samples to (1, N) tensor shape."""
    samples = np.zeros(512, dtype=np.float32)
    frame = AudioFrame.create(samples=samples, sample_rate=16000, timestamp=time.time())

    prepared = VADAudioAdapter.prepare_samples(frame)
    assert prepared.shape == (1, 512)
    assert prepared.dtype == np.float32


def test_vad_state_machine_transitions():
    """Verify VADStateMachine speech confirmation, pause resume, and silence duration timeout."""
    started_events = []
    stopped_events = []

    def on_started(prob, ts):
        started_events.append((prob, ts))

    def on_stopped(dur, prob, sil):
        stopped_events.append((dur, prob, sil))

    cfg = VADConfiguration(
        speech_threshold=0.50,
        negative_threshold=0.35,
        speech_start_confirmation_ms=64.0,  # 2 frames at 32ms
        min_silence_duration_ms=64.0,  # 2 frames at 32ms
    )
    sm = VADStateMachine(
        config=cfg,
        on_speech_started=on_started,
        on_speech_stopped=on_stopped,
    )

    # Frame 1: prob 0.80 -> SPEECH_CANDIDATE (32ms)
    s1 = sm.process_frame(0.80, frame_duration_ms=32.0, timestamp=10.0)
    assert s1 == VADState.SPEECH_CANDIDATE
    assert len(started_events) == 0

    # Frame 2: prob 0.85 -> SPEAKING (64ms reached, triggers SpeechStarted)
    s2 = sm.process_frame(0.85, frame_duration_ms=32.0, timestamp=10.032)
    assert s2 == VADState.SPEAKING
    assert len(started_events) == 1

    # Frame 3: prob 0.20 -> SILENCE_CANDIDATE (32ms silence)
    s3 = sm.process_frame(0.20, frame_duration_ms=32.0, timestamp=10.064)
    assert s3 == VADState.SILENCE_CANDIDATE
    assert len(stopped_events) == 0

    # Frame 4: prob 0.80 -> SPEAKING (Speech resumed during pause!)
    s4 = sm.process_frame(0.80, frame_duration_ms=32.0, timestamp=10.096)
    assert s4 == VADState.SPEAKING
    assert len(stopped_events) == 0

    # Frame 5: prob 0.10 -> SILENCE_CANDIDATE (32ms silence)
    s5 = sm.process_frame(0.10, frame_duration_ms=32.0, timestamp=10.128)
    assert s5 == VADState.SILENCE_CANDIDATE

    # Frame 6: prob 0.10 -> IDLE (64ms silence reached, triggers SpeechStopped)
    s6 = sm.process_frame(0.10, frame_duration_ms=32.0, timestamp=10.160)
    assert s6 == VADState.IDLE
    assert len(stopped_events) == 1


def test_vad_state_machine_false_start_rejection():
    """Verify false start probability spike is rejected without emitting SpeechStarted."""
    started = []
    sm = VADStateMachine(
        config=VADConfiguration(speech_start_confirmation_ms=64.0),
        on_speech_started=lambda p, t: started.append(p),
    )

    # Single spike frame (32ms < 64ms)
    sm.process_frame(0.90, frame_duration_ms=32.0)
    assert sm.current_state == VADState.SPEECH_CANDIDATE

    # Probability falls below negative threshold
    sm.process_frame(0.10, frame_duration_ms=32.0)
    assert sm.current_state == VADState.IDLE
    assert len(started) == 0


def test_vad_detector_audio_frame_processing():
    """Verify VADDetector processes AudioFrames and publishes EventBus events."""
    config_mgr = ConfigurationManager()
    audio_engine = AudioEngine(config_manager=config_mgr)
    event_bus = EventBus()

    # Pre-scripted probabilities: 2 speech frames, 2 silence frames
    mock_model = MockVADModel(probabilities=[0.90, 0.90, 0.10, 0.10])
    detector = VADDetector(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        model=mock_model,
    )
    detector.vad_config.speech_start_confirmation_ms = 32.0
    detector.vad_config.min_silence_duration_ms = 32.0
    detector.initialize()

    started_events = []
    stopped_events = []
    event_bus.subscribe("SpeechStarted", lambda e: started_events.append(e))
    event_bus.subscribe("SpeechStopped", lambda e: stopped_events.append(e))

    detector.start_listening()

    # Deliver 4 frames
    for i in range(4):
        frame = AudioFrame.create(
            samples=np.zeros(512, dtype=np.float32),
            sample_rate=16000,
            timestamp=10.0 + (i * 0.032),
        )
        detector._on_audio_frame(frame)

    detector.stop_listening()
    detector.stop()

    assert len(started_events) == 1
    assert isinstance(started_events[0], SpeechStarted)
    assert len(stopped_events) == 1
    assert isinstance(stopped_events[0], SpeechStopped)


def test_three_way_voice_subsystem_coexistence():
    """Verify ClapDetector, WakeWordDetector, and VADDetector consume AudioEngine concurrently."""
    config_mgr = ConfigurationManager()
    audio_engine = AudioEngine(config_manager=config_mgr)
    event_bus = EventBus()

    clap_det = ClapDetector(
        config_manager=config_mgr, audio_engine=audio_engine, event_bus=event_bus
    )
    ww_det = WakeWordDetector(
        config_manager=config_mgr, audio_engine=audio_engine, event_bus=event_bus
    )
    vad_det = VADDetector(
        config_manager=config_mgr, audio_engine=audio_engine, event_bus=event_bus
    )

    clap_det.initialize()
    ww_det.initialize()
    vad_det.initialize()

    clap_det.start_listening()
    ww_det.start_listening()
    vad_det.start_listening()

    assert len(audio_engine.input_stream._subscribers) == 3

    # Deliver 5 frames
    for _ in range(5):
        audio_engine.input_stream._audio_callback(
            indata=np.zeros((512, 1), dtype=np.float32),
            frames=512,
            time_info=None,
            status=None,
        )

    clap_det.stop_listening()
    ww_det.stop_listening()
    vad_det.stop_listening()

    clap_det.stop()
    ww_det.stop()
    vad_det.stop()

    assert len(audio_engine.input_stream._subscribers) == 0


def test_vad_bootstrapper_integration(qapp):
    """Verify VADDetector integration into 8-step AppBootstrapper startup."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        container = result.container
        vad_detector: VADDetector = container.vad_detector()

        assert vad_detector is not None
        report = vad_detector.get_health_report()
        assert report["status"] == "HEALTHY"
        assert report["provider"] == "Silero VAD (ONNX Runtime)"
        assert "metrics" in report
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()
