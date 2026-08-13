"""Unit and integration test suite for Phase 3.3 Wake Word Detection & Voice Activation."""

import time

import numpy as np

from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.services.events.event_bus import EventBus
from app.voice.audio.audio_engine import AudioEngine
from app.voice.audio.device_manager import AudioDeviceManager
from app.voice.audio.models import AudioFrame
from app.voice.clap.clap_detector import ClapDetector
from app.voice.clap.events import DoubleClapDetected
from app.voice.wakeword import (
    WakeWordAudioAdapter,
    WakeWordConfiguration,
    WakeWordDetected,
    WakeWordDetector,
    WakeWordEvent,
    WakeWordMetrics,
    WakeWordModelProvider,
)


class MockWakeWordModelProvider(WakeWordModelProvider):
    """Mock OpenWakeWord model provider for deterministic unit testing."""

    def __init__(self, scores_to_return: list[float] | None = None) -> None:
        super().__init__()
        self.scores_to_return = scores_to_return or [0.85]
        self._is_loaded = True
        self._active_model_name = "friday"
        self._model_path = "mock:friday.onnx"

    def load_model(self) -> bool:
        self._is_loaded = True
        return True

    def predict(self, int16_samples: any) -> dict[str, float]:
        score = self.scores_to_return.pop(0) if self.scores_to_return else 0.1
        return {"friday": score}


def create_synthetic_frame() -> AudioFrame:
    """Helper factory generating a 512-sample float32 AudioFrame."""
    samples = np.random.uniform(-0.1, 0.1, 512).astype(np.float32)
    return AudioFrame.create(samples=samples, timestamp=time.time())


def test_wakeword_models_and_config():
    """Verify WakeWordConfiguration and WakeWordEvent domain models."""
    cfg = WakeWordConfiguration()
    assert cfg.enabled is True
    assert cfg.model_name == "friday"
    assert cfg.threshold == 0.70
    assert cfg.cooldown_ms == 2000

    event = WakeWordEvent(
        timestamp=100.0,
        wake_word="friday",
        score=0.88,
        threshold=0.70,
        model_id="friday",
    )
    assert event.score == 0.88
    assert event.signal_quality == "HIGH"


def test_audio_adapter_pcm_conversion():
    """Verify WakeWordAudioAdapter converts float32 to int16 PCM accurately."""
    float_samples = np.array([-1.0, 0.0, 0.5, 1.0], dtype=np.float32)
    frame = AudioFrame.create(samples=float_samples, timestamp=1.0)

    int16_samples = WakeWordAudioAdapter.adapt_frame(frame)
    assert int16_samples.dtype == np.int16
    assert int16_samples[0] == -32767
    assert int16_samples[1] == 0
    assert int16_samples[3] == 32767


def test_model_provider_resolution():
    """Verify WakeWordModelProvider pretrained resolution and status reporting."""
    provider = WakeWordModelProvider()
    path = provider.resolve_model_path("friday")
    assert path is not None or provider.active_model_name == "friday"


def test_wakeword_detector_mock_inference_and_threshold():
    """Verify WakeWordDetector score threshold evaluation and event publishing."""
    config_mgr = ConfigurationManager()
    event_bus = EventBus()

    # Mock provider returning low score (0.4) then high score (0.85)
    mock_provider = MockWakeWordModelProvider(scores_to_return=[0.4, 0.85])
    metrics = WakeWordMetrics()

    detector = WakeWordDetector(
        config_manager=config_mgr,
        event_bus=event_bus,
        model_provider=mock_provider,
        metrics=metrics,
    )
    detector.initialize()

    detections = []

    def on_detection(evt: WakeWordDetected):
        detections.append(evt)

    detector.subscribe_activation(on_detection)

    # 1. Low Score Frame (0.4 < 0.70 threshold) -> Rejected
    f1 = create_synthetic_frame()
    f1.timestamp = 10.0
    evt1 = detector.process_frame(f1)
    assert evt1 is None
    assert len(detections) == 0

    # 2. High Score Frame (0.85 >= 0.70 threshold) -> Wake Word Detected!
    f2 = create_synthetic_frame()
    f2.timestamp = 10.5
    evt2 = detector.process_frame(f2)
    assert evt2 is not None
    assert evt2.score == 0.85
    assert len(detections) == 1
    assert detections[0].wake_word == "friday"

    snapshot = metrics.snapshot()
    assert snapshot["valid_detections_count"] == 1
    assert snapshot["rejected_predictions_count"] == 1


def test_wakeword_detector_cooldown():
    """Verify refractory cooldown suppresses duplicate continuous high-score frame predictions."""
    config_mgr = ConfigurationManager()
    event_bus = EventBus()
    mock_provider = MockWakeWordModelProvider(scores_to_return=[0.90, 0.92, 0.95])
    metrics = WakeWordMetrics()

    detector = WakeWordDetector(
        config_manager=config_mgr,
        event_bus=event_bus,
        model_provider=mock_provider,
        metrics=metrics,
    )
    detector.initialize()

    detections = []
    detector.subscribe_activation(lambda evt: detections.append(evt))

    # Frame 1 at t=10.0 -> Detection 1
    f1 = create_synthetic_frame()
    f1.timestamp = 10.0
    detector.process_frame(f1)
    assert len(detections) == 1

    # Frame 2 at t=10.5 (+500ms < 2000ms cooldown) -> Refractory suppression
    f2 = create_synthetic_frame()
    f2.timestamp = 10.5
    detector.process_frame(f2)
    assert len(detections) == 1  # Still 1

    snapshot = metrics.snapshot()
    assert snapshot["cooldown_suppressions_count"] == 1


def test_dual_alternative_activation_architecture():
    """Verify Double Clap (Phase 3.2) and Wake Word (Phase 3.3) act as independent activation paths."""
    config_mgr = ConfigurationManager()
    device_mgr = AudioDeviceManager()
    event_bus = EventBus()

    audio_engine = AudioEngine(
        config_manager=config_mgr, device_manager=device_mgr, event_bus=event_bus
    )
    audio_engine.initialize()

    clap_detector = ClapDetector(
        config_manager=config_mgr, audio_engine=audio_engine, event_bus=event_bus
    )
    clap_detector.initialize()

    mock_provider = MockWakeWordModelProvider(scores_to_return=[0.90])
    ww_detector = WakeWordDetector(
        config_manager=config_mgr,
        audio_engine=audio_engine,
        event_bus=event_bus,
        model_provider=mock_provider,
    )
    ww_detector.initialize()

    activations = []

    def on_clap(evt: DoubleClapDetected):
        activations.append("CLAP")

    def on_wake_word(evt: WakeWordDetected):
        activations.append("WAKE_WORD")

    clap_detector.subscribe_activation(on_clap)
    ww_detector.subscribe_activation(on_wake_word)

    try:
        # Trigger Wake Word Frame
        f_ww = create_synthetic_frame()
        f_ww.timestamp = 100.0
        ww_detector.process_frame(f_ww)

        assert len(activations) == 1
        assert activations[0] == "WAKE_WORD"
    finally:
        clap_detector.stop()
        ww_detector.stop()
        audio_engine.stop()


def test_wakeword_detector_bootstrapper_integration(qapp):
    """Verify WakeWordDetector integration into 8-step AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        container = result.container
        wakeword_detector: WakeWordDetector = container.wakeword_detector()

        assert wakeword_detector is not None
        report = wakeword_detector.get_health_report()
        assert report["status"] == "HEALTHY"
        assert report["provider"] == "OpenWakeWord"
        assert "metrics" in report
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()
