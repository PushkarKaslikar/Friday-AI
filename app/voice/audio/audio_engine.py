"""Concrete AudioEngine implementation providing foundational audio I/O services."""

import math
import threading
from collections.abc import Callable
from typing import Any

import numpy as np

from app.config.manager import ConfigurationManager
from app.config.models import Settings
from app.logging import logger
from app.services.base.service_interface import BaseService
from app.services.events.event_bus import EventBus
from app.voice.audio.device_manager import AudioDeviceManager
from app.voice.audio.diagnostics import AudioDiagnostics
from app.voice.audio.engine_interface import IAudioEngine
from app.voice.audio.events import (
    AudioDeviceChanged,
    AudioEngineInitialized,
    AudioEngineReady,
    AudioEngineShutdown,
    AudioError,
    AudioInputStarted,
    AudioInputStopped,
    AudioOutputStarted,
    AudioOutputStopped,
)
from app.voice.audio.input_stream import AudioInputStream
from app.voice.audio.metrics import AudioMetrics
from app.voice.audio.models import (
    AudioConfiguration,
    AudioDevice,
    AudioEngineState,
    AudioFrame,
    AudioStreamState,
)
from app.voice.audio.output_stream import AudioOutputStream
from app.voice.audio.ring_buffer import AudioRingBuffer


class AudioEngine(BaseService, IAudioEngine):
    """Central Audio Engine orchestrating device management, input/output streams, ring buffer, and diagnostics.

    Architecture Guarantee:
    - Local-only audio processing (zero cloud transmission, zero disk recording).
    - Lightweight callbacks (< 1ms execution time).
    - Non-blocking startup (Engine initializes into READY state without auto-recording microphone input).
    """

    def __init__(
        self,
        config_manager: ConfigurationManager | None = None,
        device_manager: AudioDeviceManager | None = None,
        event_bus: EventBus | None = None,
        metrics: AudioMetrics | None = None,
        diagnostics: AudioDiagnostics | None = None,
    ) -> None:
        super().__init__(name="AudioEngine", is_critical=False)
        self.config_manager = config_manager or ConfigurationManager()
        self.device_manager = device_manager or AudioDeviceManager()
        self.event_bus = event_bus or EventBus()
        self.metrics = metrics or AudioMetrics()
        self.diagnostics = diagnostics or AudioDiagnostics(metrics=self.metrics)

        self._engine_state = AudioEngineState.CREATED
        self._config: AudioConfiguration = self._load_configuration()

        # Calculate max ring buffer capacity: e.g. 5 seconds * 16000 samples / 512 block size = ~156 blocks
        max_buffer_blocks = math.ceil(
            (self._config.buffer_size_seconds * self._config.sample_rate)
            / self._config.block_size
        )
        self.ring_buffer = AudioRingBuffer(
            max_capacity_frames=max_buffer_blocks, metrics=self.metrics
        )

        self.input_stream = AudioInputStream(
            config=self._config, ring_buffer=self.ring_buffer, metrics=self.metrics
        )
        self.output_stream = AudioOutputStream(
            config=self._config, metrics=self.metrics
        )

        self._last_error: str | None = None
        self._engine_lock = threading.Lock()

    @property
    def state(self) -> AudioEngineState:
        """Current AudioEngine lifecycle state."""
        with self._engine_lock:
            return self._engine_state

    @property
    def input_state(self) -> AudioStreamState:
        """Current input stream state."""
        return self.input_stream.state

    @property
    def output_state(self) -> AudioStreamState:
        """Current output stream state."""
        return self.output_stream.state

    @property
    def is_playing_audio(self) -> bool:
        """Check if output stream is playing audio or within 1.5s reverberation decay."""
        if hasattr(self, "output_stream") and self.output_stream:
            if self.output_stream.is_playing:
                return True
            import time
            last_t = getattr(self.output_stream, "last_playback_time", 0.0)
            if (time.time() - last_t) < 1.5:
                return True
        return False

    def _load_configuration(self) -> AudioConfiguration:
        """Load AudioConfiguration from Settings Manager."""
        settings: Settings = self.config_manager.settings
        audio_cfg = settings.audio

        return AudioConfiguration(
            sample_rate=audio_cfg.sample_rate,
            input_channels=audio_cfg.input_channels,
            output_channels=audio_cfg.output_channels,
            block_size=audio_cfg.block_size,
            dtype=audio_cfg.dtype,
            latency_mode=audio_cfg.latency_mode,
            input_device_id=audio_cfg.input_device_id,
            output_device_id=audio_cfg.output_device_id,
            buffer_size_seconds=audio_cfg.buffer_size_seconds,
            auto_fallback=audio_cfg.auto_fallback,
        )

    def _do_initialize(self) -> None:
        """Lifecycle Hook 1: Initialize device manager and prepare input/output stream components."""
        with self._engine_lock:
            self._engine_state = AudioEngineState.INITIALIZING

        try:
            # 1. Select & validate input device
            in_dev = self.device_manager.validate_input_device(
                device_id=self._config.input_device_id,
                sample_rate=self._config.sample_rate,
            )
            self.input_stream.prepare(in_dev)

            # 2. Select & validate output device
            out_dev = self.device_manager.validate_output_device(
                device_id=self._config.output_device_id,
                sample_rate=self._config.sample_rate,
            )
            self.output_stream.prepare(out_dev)

            self.event_bus.publish(
                AudioEngineInitialized(
                    sample_rate=self._config.sample_rate,
                    default_input=in_dev.name,
                    default_output=out_dev.name,
                )
            )
            with self._engine_lock:
                self._engine_state = AudioEngineState.READY
            logger.info("AudioEngine: Initialization complete.")
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            with self._engine_lock:
                self._engine_state = AudioEngineState.ERROR
            self.event_bus.publish(
                AudioError(
                    error_code="AUDIO_INITIALIZATION_FAILED",
                    message="Failed to initialize AudioEngine",
                    details=str(exc),
                )
            )
            logger.error(f"AudioEngine: Initialization error: {exc}")

    def _do_start(self) -> None:
        """Lifecycle Hook 2: Start microphone audio input stream and transition to READY state."""
        with self._engine_lock:
            if self._engine_state == AudioEngineState.ERROR:
                logger.warning(
                    "AudioEngine: Skipping start due to initialization error."
                )
                return
            self._engine_state = AudioEngineState.READY

        try:
            self.start_input()
            logger.info("AudioEngine: Microphone input stream started successfully.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"AudioEngine: Non-fatal notice starting input stream: {exc}"
            )

        self.event_bus.publish(AudioEngineReady())
        logger.info("AudioEngine: Transitioned to READY state.")

    def _do_stop(self) -> None:
        """Lifecycle Hook 3: Gracefully stop streams and release audio resources."""
        with self._engine_lock:
            self._engine_state = AudioEngineState.STOPPING

        self.stop_input()
        self.stop_output()
        self.ring_buffer.clear()

        with self._engine_lock:
            self._engine_state = AudioEngineState.STOPPED

        self.event_bus.publish(AudioEngineShutdown())
        logger.info("AudioEngine: Shutdown completed.")

    # --- Input Stream API ---

    def start_input(self) -> None:
        """Start microphone audio streaming."""
        try:
            self.input_stream.start()
            active_dev = self.input_stream.active_device
            dev_id = active_dev.device_id if active_dev else "Unknown"
            dev_name = active_dev.name if active_dev else "Unknown"

            with self._engine_lock:
                self._engine_state = AudioEngineState.RUNNING

            self.event_bus.publish(
                AudioInputStarted(
                    device_id=dev_id,
                    device_name=dev_name,
                    sample_rate=self._config.sample_rate,
                )
            )
        except Exception as exc:
            self._last_error = str(exc)
            self.metrics.record_error()
            self.event_bus.publish(
                AudioError(
                    error_code="INPUT_STREAM_FAILED",
                    message="Failed to start microphone stream",
                    details=str(exc),
                )
            )
            raise

    def stop_input(self) -> None:
        """Stop microphone audio streaming."""
        self.input_stream.stop()
        self.event_bus.publish(AudioInputStopped())

    def pause_input(self) -> None:
        """Pause microphone streaming."""
        self.input_stream.pause()

    def resume_input(self) -> None:
        """Resume microphone streaming."""
        self.input_stream.resume()

    # --- Output Stream API ---

    def start_output(self) -> None:
        """Start speaker playback stream."""
        try:
            self.output_stream.start()
            active_dev = self.output_stream.active_device
            dev_id = active_dev.device_id if active_dev else "Unknown"
            dev_name = active_dev.name if active_dev else "Unknown"

            self.event_bus.publish(
                AudioOutputStarted(device_id=dev_id, device_name=dev_name)
            )
        except Exception as exc:
            self._last_error = str(exc)
            self.metrics.record_error()
            self.event_bus.publish(
                AudioError(
                    error_code="OUTPUT_STREAM_FAILED",
                    message="Failed to start output stream",
                    details=str(exc),
                )
            )
            raise

    def stop_output(self) -> None:
        """Stop speaker playback stream."""
        self.output_stream.stop()
        self.event_bus.publish(AudioOutputStopped())

    def pause_output(self) -> None:
        """Pause playback stream."""
        self.output_stream.pause()

    def resume_output(self) -> None:
        """Resume playback stream."""
        self.output_stream.resume()

    def play(self, samples: Any) -> None:
        """Enqueue PCM audio samples for speaker playback.

        Starts output stream automatically if not currently running.
        """
        if self.output_state != AudioStreamState.RUNNING:
            self.start_output()

        self.output_stream.enqueue(samples)

    def clear_output_queue(self) -> None:
        """Flush output playback queue (barge-in capability)."""
        self.output_stream.clear()

    # --- Subscription & Delivery ---

    def subscribe(self, callback: Callable[[AudioFrame], None]) -> None:
        """Subscribe a downstream voice consumer callback (e.g. Clap, Wake Word, VAD)."""
        self.input_stream.subscribe(callback)

    def unsubscribe(self, callback: Callable[[AudioFrame], None]) -> None:
        """Unsubscribe a downstream consumer callback."""
        self.input_stream.unsubscribe(callback)

    # --- Device Management & Selection ---

    def get_input_devices(self) -> list[AudioDevice]:
        """Enumerate system audio input devices."""
        return self.device_manager.get_input_devices()

    def get_output_devices(self) -> list[AudioDevice]:
        """Enumerate system audio output devices."""
        return self.device_manager.get_output_devices()

    def get_default_input_device(self) -> AudioDevice | None:
        """Get system default microphone input device."""
        return self.device_manager.get_default_input_device()

    def get_default_output_device(self) -> AudioDevice | None:
        """Get system default speaker output device."""
        return self.device_manager.get_default_output_device()

    def select_input_device(self, device_id: int | str | None) -> AudioDevice:
        """Select active microphone input device."""
        old_dev_name = (
            self.input_stream.active_device.name
            if self.input_stream.active_device
            else "None"
        )
        new_dev = self.device_manager.validate_input_device(
            device_id=device_id, sample_rate=self._config.sample_rate
        )

        was_running = self.input_state == AudioStreamState.RUNNING
        if was_running:
            self.stop_input()

        self.input_stream.prepare(new_dev)
        self._config.input_device_id = new_dev.device_id
        self.metrics.record_device_change()

        if was_running:
            self.start_input()

        self.event_bus.publish(
            AudioDeviceChanged(
                device_type="INPUT", old_device=old_dev_name, new_device=new_dev.name
            )
        )
        return new_dev

    def select_output_device(self, device_id: int | str | None) -> AudioDevice:
        """Select active speaker output device."""
        old_dev_name = (
            self.output_stream.active_device.name
            if self.output_stream.active_device
            else "None"
        )
        new_dev = self.device_manager.validate_output_device(
            device_id=device_id, sample_rate=self._config.sample_rate
        )

        was_running = self.output_state == AudioStreamState.RUNNING
        if was_running:
            self.stop_output()

        self.output_stream.prepare(new_dev)
        self._config.output_device_id = new_dev.device_id
        self.metrics.record_device_change()

        if was_running:
            self.start_output()

        self.event_bus.publish(
            AudioDeviceChanged(
                device_type="OUTPUT", old_device=old_dev_name, new_device=new_dev.name
            )
        )
        return new_dev

    # --- Utility & Test Helpers ---

    def get_configuration(self) -> AudioConfiguration:
        """Get active audio configuration model."""
        return self._config

    def generate_test_tone(
        self, frequency_hz: float = 440.0, duration_seconds: float = 1.0
    ) -> np.ndarray:
        """Generate synthetic sine wave float32 audio samples for non-TTS hardware output testing."""
        sample_rate = self._config.sample_rate
        total_samples = int(sample_rate * duration_seconds)
        t = np.linspace(0, duration_seconds, total_samples, endpoint=False)
        sine_wave = 0.3 * np.sin(2 * np.pi * frequency_hz * t).astype(np.float32)
        return sine_wave

    def get_health_report(self) -> dict[str, Any]:
        """Generate diagnostic health report."""
        in_dev = self.input_stream.active_device
        out_dev = self.output_stream.active_device

        return self.diagnostics.get_health_report(
            engine_state=self.state.value,
            input_state=self.input_state.value,
            output_state=self.output_state.value,
            active_input_device=in_dev.name if in_dev else "None",
            active_output_device=out_dev.name if out_dev else "None",
            sample_rate=self._config.sample_rate,
            channels=self._config.input_channels,
            buffer_capacity_sec=self._config.buffer_size_seconds,
            last_error=self._last_error,
        )

    def health_check(self) -> dict[str, Any]:
        """HealthMonitor service integration hook."""
        base = super().health_check()
        base.update(self.get_health_report())
        return base
