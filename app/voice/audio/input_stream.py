"""Audio input stream wrapper managing real-time microphone capture using sounddevice."""

import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np
import sounddevice as sd

from app.logging import logger
from app.voice.audio.metrics import AudioMetrics
from app.voice.audio.models import (
    AudioConfiguration,
    AudioDevice,
    AudioFrame,
    AudioStreamState,
)
from app.voice.audio.ring_buffer import AudioRingBuffer


class AudioInputStream:
    """Encapsulates sounddevice.InputStream for low-latency microphone audio streaming.

    Strict Callback Constraint:
    The C audio callback MUST remain lightweight (< 1ms).
    It only timestamps, converts samples to float32, creates AudioFrame, pushes to ring buffer,
    dispatches to subscribers, and returns immediately.
    """

    def __init__(
        self,
        config: AudioConfiguration,
        ring_buffer: AudioRingBuffer,
        metrics: AudioMetrics | None = None,
    ) -> None:
        self.config = config
        self.ring_buffer = ring_buffer
        self.metrics = metrics or AudioMetrics()

        self._state = AudioStreamState.NOT_INITIALIZED
        self._stream: sd.InputStream | None = None
        self._active_device: AudioDevice | None = None
        self._subscribers: list[Callable[[AudioFrame], None]] = []
        self._lock = threading.Lock()

    @property
    def state(self) -> AudioStreamState:
        """Current stream lifecycle state."""
        with self._lock:
            return self._state

    @property
    def active_device(self) -> AudioDevice | None:
        """Active hardware input device."""
        with self._lock:
            return self._active_device

    def subscribe(self, callback: Callable[[AudioFrame], None]) -> None:
        """Subscribe a downstream consumer callback (e.g. Clap, Wake Word, VAD)."""
        with self._lock:
            if callback not in self._subscribers:
                self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[AudioFrame], None]) -> None:
        """Remove a subscriber callback."""
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)

    def prepare(self, device: AudioDevice) -> None:
        """Prepare stream parameters without starting audio capture."""
        with self._lock:
            self._active_device = device
            self._state = AudioStreamState.READY
            logger.info(
                f"AudioInputStream: Prepared for device '{device.name}' "
                f"({self.config.sample_rate}Hz, {self.config.input_channels} ch)."
            )

    def start(self) -> None:
        """Start microphone audio streaming."""
        with self._lock:
            if self._state == AudioStreamState.RUNNING:
                return

            if not self._active_device:
                self._state = AudioStreamState.ERROR
                raise RuntimeError(
                    "AudioInputStream: Cannot start stream. No input device prepared."
                )

            dev_id = self._active_device.device_id
            dev_idx = (
                int(dev_id)
                if isinstance(dev_id, int) or str(dev_id).isdigit()
                else None
            )

            try:
                self._stream = sd.InputStream(
                    device=dev_idx,
                    samplerate=self.config.sample_rate,
                    channels=self.config.input_channels,
                    blocksize=self.config.block_size,
                    dtype=self.config.dtype,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._state = AudioStreamState.RUNNING
                self.metrics.start_input_timer()
                logger.info(
                    f"AudioInputStream: Started stream on device '{self._active_device.name}'."
                )
            except Exception as exc:
                self._state = AudioStreamState.ERROR
                logger.error(
                    f"AudioInputStream: Failed to start sounddevice stream: {exc}"
                )
                raise RuntimeError(f"Failed to start microphone stream: {exc}") from exc

    def pause(self) -> None:
        """Pause microphone streaming."""
        with self._lock:
            if self._stream and self._state == AudioStreamState.RUNNING:
                self._stream.stop()
                self._state = AudioStreamState.PAUSED
                self.metrics.stop_input_timer()
                logger.info("AudioInputStream: Paused stream.")

    def resume(self) -> None:
        """Resume paused microphone streaming."""
        with self._lock:
            if self._stream and self._state == AudioStreamState.PAUSED:
                self._stream.start()
                self._state = AudioStreamState.RUNNING
                self.metrics.start_input_timer()
                logger.info("AudioInputStream: Resumed stream.")

    def stop(self) -> None:
        """Stop microphone streaming and release stream resources."""
        with self._lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"AudioInputStream: Error closing stream: {exc}")
                finally:
                    self._stream = None

            self._state = AudioStreamState.STOPPED
            self.metrics.stop_input_timer()
            logger.info("AudioInputStream: Stopped stream.")

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        """Lightweight real-time audio callback invoked by C sounddevice thread.

        MUST NOT perform disk I/O, AI inference, or PySide UI calls.
        """
        cb_start = time.perf_counter()
        capture_timestamp = time.time()

        if status:
            logger.warning(f"AudioInputStream: Callback status warning: {status}")

        # Flatten or copy mono/stereo buffer
        samples = np.copy(indata).astype(np.float32)
        if self.config.input_channels == 1 and len(samples.shape) > 1:
            samples = samples.squeeze(axis=-1)

        # Build AudioFrame abstraction
        frame = AudioFrame.create(
            samples=samples,
            timestamp=capture_timestamp,
            sample_rate=self.config.sample_rate,
            channels=self.config.input_channels,
            metadata={"status_flags": str(status) if status else "OK"},
        )

        # Push frame into ring buffer
        self.ring_buffer.push(frame)

        # Dispatch frame to subscribers
        with self._lock:
            subscribers_copy = list(self._subscribers)

        for callback in subscribers_copy:
            try:
                callback(frame)
            except Exception as exc:  # noqa: BLE001
                logger.error(f"AudioInputStream: Subscriber callback exception: {exc}")

        cb_duration_ms = (time.perf_counter() - cb_start) * 1000.0
        self.metrics.record_input_frame(
            frame_sample_count=frames, callback_duration_ms=cb_duration_ms
        )
