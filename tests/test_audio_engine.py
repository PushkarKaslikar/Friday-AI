"""Unit and integration test suite for Phase 3.1 Audio Engine Foundation."""

import time

import numpy as np
import pytest

from app.bootstrap.bootstrapper import AppBootstrapper
from app.config.manager import ConfigurationManager
from app.services.events.event_bus import EventBus
from app.voice.audio import (
    AudioConfiguration,
    AudioDevice,
    AudioDeviceManager,
    AudioDiagnostics,
    AudioEngine,
    AudioEngineState,
    AudioFrame,
    AudioMetrics,
    AudioOutputStream,
    AudioRingBuffer,
    AudioStreamState,
)


def test_audio_models():
    """Verify AudioDevice, AudioConfiguration, and AudioFrame data models."""
    dev = AudioDevice(
        device_id=0,
        name="Mock Microphone",
        is_input=True,
        is_output=False,
        max_input_channels=1,
        default_sample_rate=16000,
    )
    assert dev.device_id == 0
    assert dev.is_input is True
    assert dev.is_output is False

    cfg = AudioConfiguration()
    assert cfg.sample_rate == 16000
    assert cfg.input_channels == 1
    assert cfg.output_channels == 2
    assert cfg.dtype == "float32"

    samples = np.zeros(512, dtype=np.float32)
    now = time.time()
    frame = AudioFrame.create(
        samples=samples, timestamp=now, sample_rate=16000, channels=1
    )
    assert frame.frame_count == 512
    assert frame.duration == pytest.approx(0.032, abs=1e-4)
    assert frame.timestamp == now


def test_audio_ring_buffer_drop_oldest():
    """Verify AudioRingBuffer bounded capacity and drop-oldest backpressure policy."""
    metrics = AudioMetrics()
    buffer = AudioRingBuffer(max_capacity_frames=3, metrics=metrics)

    assert buffer.is_empty is True
    assert buffer.capacity == 3

    f1 = AudioFrame.create(np.ones(100), timestamp=1.0)
    f2 = AudioFrame.create(np.ones(100) * 2, timestamp=2.0)
    f3 = AudioFrame.create(np.ones(100) * 3, timestamp=3.0)
    f4 = AudioFrame.create(np.ones(100) * 4, timestamp=4.0)

    buffer.push(f1)
    buffer.push(f2)
    buffer.push(f3)
    assert buffer.is_full is True
    assert buffer.size == 3

    # Push 4th frame -> overflows and drops f1 (oldest)
    buffer.push(f4)
    assert buffer.size == 3
    assert buffer.peek().timestamp == 2.0  # f2 is now oldest

    snapshot = metrics.snapshot()
    assert snapshot["buffer_overflow_count"] == 1
    assert snapshot["dropped_frames"] == 1

    popped = buffer.pop()
    assert popped.timestamp == 2.0
    assert buffer.size == 2

    buffer.clear()
    assert buffer.is_empty is True


def test_audio_device_manager():
    """Verify AudioDeviceManager device discovery and device validation logic."""
    dm = AudioDeviceManager()
    all_devs = dm.get_all_devices()
    assert isinstance(all_devs, list)

    in_devs = dm.get_input_devices()
    out_devs = dm.get_output_devices()
    assert all(d.is_input for d in in_devs)
    assert all(d.is_output for d in out_devs)

    # Validating default input and output device fallback
    default_in = dm.validate_input_device(None)
    assert default_in is not None
    assert default_in.is_input is True

    default_out = dm.validate_output_device(None)
    assert default_out is not None
    assert default_out.is_output is True


def test_audio_output_stream_queue():
    """Verify AudioOutputStream queueing, playback simulation, and barge-in clear."""
    cfg = AudioConfiguration()
    metrics = AudioMetrics()
    stream = AudioOutputStream(config=cfg, metrics=metrics)

    dev = AudioDevice(device_id=0, name="Mock Speaker", is_output=True)
    stream.prepare(dev)
    assert stream.state == AudioStreamState.READY

    samples = np.sin(np.linspace(0, 1, 1000)).astype(np.float32)
    stream.enqueue(samples)
    assert stream.is_playing is True

    # Test barge-in clear
    stream.clear()
    assert stream.is_playing is False


def test_audio_engine_lifecycle():
    """Verify AudioEngine state transitions and non-blocking startup."""
    config_mgr = ConfigurationManager()
    device_mgr = AudioDeviceManager()
    event_bus = EventBus()
    metrics = AudioMetrics()
    diagnostics = AudioDiagnostics(metrics=metrics)

    engine = AudioEngine(
        config_manager=config_mgr,
        device_manager=device_mgr,
        event_bus=event_bus,
        metrics=metrics,
        diagnostics=diagnostics,
    )

    assert engine.state == AudioEngineState.CREATED

    # Start service lifecycle
    engine.initialize()
    assert engine.state in (AudioEngineState.READY, AudioEngineState.ERROR)

    engine.start()
    # Microphones start in READY / STOPPED state (NO auto-recording on startup)
    assert engine.input_state in (
        AudioStreamState.STOPPED,
        AudioStreamState.NOT_INITIALIZED,
        AudioStreamState.READY,
    )

    report = engine.get_health_report()
    assert "status" in report
    assert "metrics" in report

    # Test synthetic test tone generator
    tone = engine.generate_test_tone(frequency_hz=440.0, duration_seconds=0.5)
    assert len(tone) == int(16000 * 0.5)
    assert isinstance(tone, np.ndarray)

    engine.stop()
    assert engine.state == AudioEngineState.STOPPED


def test_audio_engine_subscriber_dispatch():
    """Verify AudioEngine subscriber callback frame dispatch."""
    config_mgr = ConfigurationManager()
    device_mgr = AudioDeviceManager()
    event_bus = EventBus()
    metrics = AudioMetrics()

    engine = AudioEngine(
        config_manager=config_mgr,
        device_manager=device_mgr,
        event_bus=event_bus,
        metrics=metrics,
    )
    engine.initialize()

    received_frames = []

    def subscriber(frame: AudioFrame):
        received_frames.append(frame)

    engine.subscribe(subscriber)
    assert subscriber in engine.input_stream._subscribers

    # Push simulated frame directly into input stream callback
    dummy_input = np.zeros((512, 1), dtype=np.float32)
    engine.input_stream._audio_callback(dummy_input, 512, None, None)

    assert len(received_frames) == 1
    assert received_frames[0].frame_count == 512

    engine.unsubscribe(subscriber)
    assert subscriber not in engine.input_stream._subscribers


def test_audio_engine_bootstrapper_integration(qapp):
    """Verify AudioEngine integration into 8-step AppBootstrapper."""
    bootstrapper = AppBootstrapper()
    try:
        result = bootstrapper.run()
        assert result.success is True

        container = result.container
        audio_engine: AudioEngine = container.audio_engine()

        assert audio_engine is not None
        assert audio_engine.state in (AudioEngineState.READY, AudioEngineState.RUNNING)
        report = audio_engine.get_health_report()
        assert report["status"] == "HEALTHY"
    finally:
        if bootstrapper.service_manager:
            bootstrapper.service_manager.stop_all()
        if bootstrapper.container:
            bootstrapper.container.reset_singletons()
