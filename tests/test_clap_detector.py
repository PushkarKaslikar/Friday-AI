"""Unit and integration test suite for Phase 3.2 Double-Clap Detection & Activation."""

import time

import numpy as np
import pytest

from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.services.events.event_bus import EventBus
from app.voice.audio.audio_engine import AudioEngine
from app.voice.audio.device_manager import AudioDeviceManager
from app.voice.audio.models import AudioFrame
from app.voice.clap import (
    ClapConfiguration,
    ClapDetector,
    ClapEvent,
    ClapMetrics,
    ClapSignalProcessor,
    ClapState,
    DoubleClapDetected,
    DoubleClapStateMachine,
)


def create_synthetic_clap_frame(
    sample_rate: int = 16000,
    frame_len: int = 512,
    peak_amp: float = 0.6,
    duration_samples: int = 300,
) -> AudioFrame:
    """Helper factory generating a synthetic sharp impulse AudioFrame mimicking a human clap."""
    samples = np.random.normal(0, 0.001, frame_len).astype(np.float32)

    # Insert sharp transient impulse with exponential decay burst
    start_idx = 50
    dur = min(frame_len - start_idx, duration_samples)
    t = np.arange(dur)
    decay = peak_amp * np.exp(-t / 80.0) * np.sin(2 * np.pi * 800 * t / sample_rate)
    samples[start_idx : start_idx + dur] += decay.astype(np.float32)

    return AudioFrame.create(
        samples=samples, timestamp=time.time(), sample_rate=sample_rate
    )


def create_synthetic_speech_frame(
    sample_rate: int = 16000, frame_len: int = 512, amp: float = 0.2
) -> AudioFrame:
    """Helper factory generating a continuous sine wave mimicking speech or music."""
    t = np.linspace(0, 0.032, frame_len)
    samples = (amp * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
    return AudioFrame.create(
        samples=samples, timestamp=time.time(), sample_rate=sample_rate
    )


def test_clap_models_and_config():
    """Verify ClapConfiguration and ClapEvent domain models."""
    cfg = ClapConfiguration()
    assert cfg.min_clap_interval_ms == 150
    assert cfg.max_clap_interval_ms == 1000
    assert cfg.cooldown_ms == 2000
    assert cfg.confidence_threshold == 0.65

    event = ClapEvent(
        timestamp=100.0,
        confidence=0.85,
        peak_amplitude=0.6,
        energy=0.02,
        duration=25.0,
        signal_quality="HIGH",
    )
    assert event.confidence == 0.85
    assert event.signal_quality == "HIGH"


def test_clap_signal_processor():
    """Verify ClapSignalProcessor transient analysis and false-positive noise rejection."""
    processor = ClapSignalProcessor()
    assert processor.noise_floor == pytest.approx(0.001, abs=1e-4)

    # Test silence -> returns None
    silence_frame = AudioFrame.create(np.zeros(512, dtype=np.float32), timestamp=1.0)
    assert processor.process_frame(silence_frame) is None

    # Test continuous speech sine wave -> rejected (crest factor / energy profile)
    speech_frame = create_synthetic_speech_frame(amp=0.1)
    assert processor.process_frame(speech_frame) is None

    # Test sharp clap impulse -> returns validated ClapEvent
    clap_frame = create_synthetic_clap_frame(peak_amp=0.6, duration_samples=300)
    clap_event = processor.process_frame(clap_frame)

    assert clap_event is not None
    assert clap_event.confidence >= 0.65
    assert clap_event.peak_amplitude >= 0.15


def test_double_clap_state_machine_activation():
    """Verify DoubleClapStateMachine state transitions, timing window, and cooldown."""
    metrics = ClapMetrics()
    sm = DoubleClapStateMachine(metrics=metrics)
    assert sm.state == ClapState.IDLE

    c1 = ClapEvent(
        timestamp=10.0, confidence=0.8, peak_amplitude=0.5, energy=0.01, duration=20.0
    )
    c2 = ClapEvent(
        timestamp=10.3,
        confidence=0.85,
        peak_amplitude=0.55,
        energy=0.012,
        duration=22.0,
    )

    # First Clap -> Transitions to WAITING_FOR_SECOND_CLAP
    activated1, _ = sm.process_clap_event(c1)
    assert activated1 is False
    assert sm.state == ClapState.WAITING_FOR_SECOND_CLAP

    # Second Clap at +300ms -> Double Clap ACTIVATED!
    activated2, interval2 = sm.process_clap_event(c2)
    assert activated2 is True
    assert interval2 == pytest.approx(300.0, abs=1e-1)
    assert sm.state == ClapState.COOLDOWN

    # Third Clap during cooldown -> Refractory suppression
    c3 = ClapEvent(
        timestamp=10.6, confidence=0.9, peak_amplitude=0.6, energy=0.015, duration=20.0
    )
    activated3, _ = sm.process_clap_event(c3)
    assert activated3 is False

    snapshot = metrics.snapshot()
    assert snapshot["successful_double_claps_count"] == 1
    assert snapshot["cooldown_suppressions_count"] == 1


def test_double_clap_state_machine_too_soon():
    """Verify rejection of second clap occurring below min_clap_interval_ms (150ms)."""
    sm = DoubleClapStateMachine()
    c1 = ClapEvent(
        timestamp=10.0, confidence=0.8, peak_amplitude=0.5, energy=0.01, duration=20.0
    )
    c2 = ClapEvent(
        timestamp=10.05,
        confidence=0.85,
        peak_amplitude=0.55,
        energy=0.012,
        duration=22.0,
    )

    sm.process_clap_event(c1)
    activated, interval = sm.process_clap_event(c2)

    assert activated is False
    assert interval == pytest.approx(50.0, abs=1e-1)


def test_double_clap_state_machine_timeout():
    """Verify timing window expiration (> 1000ms) resets state machine to IDLE."""
    metrics = ClapMetrics()
    sm = DoubleClapStateMachine(metrics=metrics)

    c1 = ClapEvent(
        timestamp=10.0, confidence=0.8, peak_amplitude=0.5, energy=0.01, duration=20.0
    )
    c2 = ClapEvent(
        timestamp=12.5,
        confidence=0.85,
        peak_amplitude=0.55,
        energy=0.012,
        duration=22.0,
    )

    sm.process_clap_event(c1)
    activated, _ = sm.process_clap_event(c2)

    assert activated is False
    snapshot = metrics.snapshot()
    assert snapshot["timed_out_claps_count"] == 1


def test_clap_detector_integration_and_events():
    """Verify ClapDetector service frame processing and DoubleClapDetected event delivery."""
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
    clap_detector.start_listening()

    activations = []

    def on_activation(event: DoubleClapDetected):
        activations.append(event)

    clap_detector.subscribe_activation(on_activation)

    try:
        # Feed Clap 1
        frame1 = create_synthetic_clap_frame(peak_amp=0.6, duration_samples=300)
        frame1.timestamp = 100.0
        clap_detector.process_frame(frame1)

        # Feed Clap 2 at +300ms
        frame2 = create_synthetic_clap_frame(peak_amp=0.65, duration_samples=300)
        frame2.timestamp = 100.3
        clap_detector.process_frame(frame2)

        assert len(activations) == 1
        assert activations[0].interval_ms == pytest.approx(300.0, abs=1e-1)
    finally:
        clap_detector.stop_listening()
        clap_detector.unsubscribe_activation(on_activation)
        clap_detector.stop()
        audio_engine.stop()


def test_clap_detector_bootstrapper_integration(qapp):
    """Verify ClapDetector integration into 8-step AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        container = result.container
        clap_detector: ClapDetector = container.clap_detector()

        assert clap_detector is not None
        report = clap_detector.get_health_report()
        assert report["status"] == "HEALTHY"
        assert "metrics" in report
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()
