"""Unit and integration test suite for Speech-to-Text (STT) Subsystem.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
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
from app.voice.stt.events import TranscriptionCompleted, TranscriptionStarted
from app.voice.stt.faster_whisper_engine import FasterWhisperSTTEngine
from app.voice.stt.models import (
    STTConfiguration,
    TranscriptionResult,
    TranscriptSegment,
)
from app.voice.stt.speech_buffer import SpeechSegmentBuffer
from app.voice.stt.stt_engine_interface import ISTTEngine
from app.voice.stt.stt_service import STTService
from app.voice.vad.events import SpeechStarted, SpeechStopped
from app.voice.vad.vad_detector import VADDetector
from app.voice.wakeword.wakeword_detector import WakeWordDetector


class FakeSTTEngine(ISTTEngine):
    """Deterministic mock STT engine for unit testing without loading real Whisper models."""

    def __init__(self, script_text: str = "Open Chrome") -> None:
        self.script_text = script_text
        self._loaded = True

    def load_model(self) -> bool:
        self._loaded = True
        return True

    def transcribe(
        self, audio_samples: Any, sample_rate: int = 16000
    ) -> TranscriptionResult:
        if not isinstance(audio_samples, np.ndarray):
            audio_samples = np.array(audio_samples, dtype=np.float32)

        duration = round(len(audio_samples) / max(1, sample_rate), 2)
        proc_time = 0.05
        rtf = round(proc_time / max(0.001, duration), 3)

        if duration < 0.1:
            return TranscriptionResult(
                text="",
                duration_seconds=duration,
                status="TOO_SHORT",
            )

        return TranscriptionResult(
            text=self.script_text,
            language="en",
            language_probability=0.98,
            duration_seconds=duration,
            processing_time_seconds=proc_time,
            real_time_factor=rtf,
            segments=[
                TranscriptSegment(start=0.0, end=duration, text=self.script_text)
            ],
            model_name="fake_whisper",
            device="cpu",
            compute_type="int8",
            status="SUCCESS",
        )

    def unload_model(self) -> None:
        self._loaded = False

    @property
    def is_loaded(self) -> bool:
        return self._loaded


def test_stt_configuration_defaults():
    """Verify default STTConfiguration domain model parameters."""
    cfg = STTConfiguration()
    assert cfg.enabled is True
    assert cfg.model_name == "base"
    assert cfg.device == "auto"
    assert cfg.compute_type == "auto"
    assert cfg.beam_size == 5
    assert cfg.max_segment_duration_ms == 30000.0


def test_speech_segment_buffer_accumulation():
    """Verify SpeechSegmentBuffer frame collection, duration calculation, and bounding limits."""
    buf = SpeechSegmentBuffer(sample_rate=16000, max_duration_seconds=1.0)
    assert buf.is_collecting is False

    buf.start_collection()
    assert buf.is_collecting is True

    # Push 0.5s of samples (8000 samples)
    frame = AudioFrame.create(
        samples=np.zeros(8000, dtype=np.float32),
        sample_rate=16000,
        timestamp=time.time(),
    )
    added = buf.push_frame(frame)
    assert added is True
    assert buf.duration_seconds == 0.5

    # Finalize buffer
    audio, duration = buf.finalize()
    assert len(audio) == 8000
    assert duration == 0.5
    assert buf.is_collecting is False


def test_fake_stt_engine_transcription():
    """Verify FakeSTTEngine returns structured TranscriptionResult."""
    engine = FakeSTTEngine(script_text="Hello Friday")
    assert engine.is_loaded is True

    samples = np.zeros(16000, dtype=np.float32)  # 1.0s audio
    res = engine.transcribe(samples, sample_rate=16000)

    assert isinstance(res, TranscriptionResult)
    assert res.text == "Hello Friday"
    assert res.status == "SUCCESS"
    assert res.duration_seconds == 1.0
    assert res.language == "en"
    assert len(res.segments) == 1


def test_faster_whisper_engine_device_resolution():
    """Verify FasterWhisperSTTEngine device resolution logic."""
    cfg = STTConfiguration(device="cpu", compute_type="int8")
    engine = FasterWhisperSTTEngine(config=cfg)
    device, compute = engine._resolve_device_and_compute()
    assert device == "cpu"
    assert compute == "int8"


def test_stt_service_speech_boundary_pipeline():
    """Verify STTService speech start/stop boundary processing and EventBus publishing."""
    config_mgr = ConfigurationManager()
    audio_engine = AudioEngine(config_manager=config_mgr)
    event_bus = EventBus()

    fake_engine = FakeSTTEngine(script_text="Open Downloads")
    service = STTService(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        engine=fake_engine,
    )
    service.initialize()
    service.start_listening()

    started_events = []
    completed_events = []

    event_bus.subscribe("TranscriptionStarted", lambda e: started_events.append(e))
    event_bus.subscribe("TranscriptionCompleted", lambda e: completed_events.append(e))

    # Simulate SpeechStarted
    event_bus.publish(SpeechStarted(speech_probability=0.85))

    # Deliver audio frame (0.5s = 8000 samples)
    frame = AudioFrame.create(
        samples=np.zeros(8000, dtype=np.float32),
        sample_rate=16000,
        timestamp=time.time(),
    )
    service._on_audio_frame(frame)

    # Simulate SpeechStopped
    event_bus.publish(SpeechStopped(speech_duration=0.5, final_probability=0.15))

    # Wait for background worker execution
    time.sleep(0.3)

    service.stop_listening()
    service.stop()

    assert len(started_events) == 1
    assert isinstance(started_events[0], TranscriptionStarted)
    assert len(completed_events) == 1
    assert isinstance(completed_events[0], TranscriptionCompleted)
    assert completed_events[0].text == "Open Downloads"


def test_four_way_voice_subsystem_coexistence():
    """Verify ClapDetector, WakeWordDetector, VADDetector, and STTService consume AudioEngine concurrently."""
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
    stt_svc = STTService(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        engine=FakeSTTEngine(),
    )

    clap_det.initialize()
    ww_det.initialize()
    vad_det.initialize()
    stt_svc.initialize()

    clap_det.start_listening()
    ww_det.start_listening()
    vad_det.start_listening()
    stt_svc.start_listening()

    assert len(audio_engine.input_stream._subscribers) == 4

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
    stt_svc.stop_listening()

    clap_det.stop()
    ww_det.stop()
    vad_det.stop()
    stt_svc.stop()

    assert len(audio_engine.input_stream._subscribers) == 0


def test_stt_metrics_and_diagnostics():
    """Verify STTMetrics collection, RTF calculation, and STTDiagnostics reporting."""
    config_mgr = ConfigurationManager()
    audio_engine = AudioEngine(config_manager=config_mgr)
    event_bus = EventBus()

    service = STTService(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        engine=FakeSTTEngine(script_text="Test Metrics"),
    )
    service.initialize()

    # Direct transcription call
    samples = np.zeros(32000, dtype=np.float32)  # 2.0s
    res = service.transcribe_audio(samples)
    service.metrics.record_transcription(
        status=res.status,
        audio_duration_sec=res.duration_seconds,
        processing_time_sec=res.processing_time_seconds,
        text=res.text,
    )

    report = service.get_health_report()
    assert report["status"] == "HEALTHY"
    assert report["provider"] == "Faster-Whisper (ctranslate2)"
    assert report["metrics"]["transcriptions_total"] == 1
    assert report["metrics"]["successful_transcriptions"] == 1
    assert report["metrics"]["words_transcribed"] == 2

    service.stop()


def test_stt_bootstrapper_integration(qapp):
    """Verify STTService integration into 8-step AppBootstrapper startup."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        container = result.container
        stt_service: STTService = container.stt_service()

        assert stt_service is not None
        report = stt_service.get_health_report()
        assert report["status"] in ("HEALTHY", "DEGRADED")
        assert report["provider"] == "Faster-Whisper (ctranslate2)"
        assert "metrics" in report
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()
