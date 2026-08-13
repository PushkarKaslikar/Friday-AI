"""Audio output stream wrapper managing speaker/headphone playback using sounddevice."""

import collections
import threading
from typing import Any

import numpy as np
import sounddevice as sd

from app.logging import logger
from app.voice.audio.metrics import AudioMetrics
from app.voice.audio.models import (
    AudioConfiguration,
    AudioDevice,
    AudioStreamState,
)


class AudioOutputStream:
    """Encapsulates sounddevice.OutputStream for audio playback to speaker or headphones.

    Supports output queueing, barge-in buffer flushing (clear), pause/resume, and playback lifecycle.
    """

    def __init__(
        self,
        config: AudioConfiguration,
        metrics: AudioMetrics | None = None,
        max_queue_depth: int = 100,
    ) -> None:
        self.config = config
        self.metrics = metrics or AudioMetrics()
        self.max_queue_depth = max_queue_depth

        self._state = AudioStreamState.NOT_INITIALIZED
        self._stream: sd.OutputStream | None = None
        self._active_device: AudioDevice | None = None

        self._output_queue: collections.deque[np.ndarray] = collections.deque(
            maxlen=max_queue_depth
        )
        self._current_chunk: np.ndarray | None = None
        self._current_offset: int = 0
        self._lock = threading.Lock()

    @property
    def state(self) -> AudioStreamState:
        """Current stream lifecycle state."""
        with self._lock:
            return self._state

    @property
    def active_device(self) -> AudioDevice | None:
        """Active hardware output device."""
        with self._lock:
            return self._active_device

    @property
    def is_playing(self) -> bool:
        """Check if output queue contains pending playback audio."""
        with self._lock:
            return len(self._output_queue) > 0 or self._current_chunk is not None

    def prepare(self, device: AudioDevice) -> None:
        """Prepare output stream parameters without starting playback stream."""
        with self._lock:
            self._active_device = device
            self._state = AudioStreamState.READY
            logger.info(
                f"AudioOutputStream: Prepared for device '{device.name}' "
                f"({self.config.sample_rate}Hz, {self.config.output_channels} ch)."
            )

    def start(self) -> None:
        """Start audio playback stream."""
        with self._lock:
            if self._state == AudioStreamState.RUNNING:
                return

            if not self._active_device:
                self._state = AudioStreamState.ERROR
                raise RuntimeError(
                    "AudioOutputStream: Cannot start stream. No output device prepared."
                )

            dev_id = self._active_device.device_id
            dev_idx = (
                int(dev_id)
                if isinstance(dev_id, int) or str(dev_id).isdigit()
                else None
            )

            try:
                self._stream = sd.OutputStream(
                    device=dev_idx,
                    samplerate=self.config.sample_rate,
                    channels=self.config.output_channels,
                    blocksize=self.config.block_size,
                    dtype=self.config.dtype,
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._state = AudioStreamState.RUNNING
                self.metrics.start_output_timer()
                logger.info(
                    f"AudioOutputStream: Started stream on device '{self._active_device.name}'."
                )
            except Exception as exc:
                self._state = AudioStreamState.ERROR
                logger.error(
                    f"AudioOutputStream: Failed to start sounddevice stream: {exc}"
                )
                raise RuntimeError(f"Failed to start speaker stream: {exc}") from exc

    def enqueue(self, samples: np.ndarray) -> None:
        """Enqueue PCM numpy audio samples for playback."""
        arr = np.asarray(samples, dtype=np.float32)

        # Ensure correct channel layout
        if self.config.output_channels == 2 and len(arr.shape) == 1:
            arr = np.column_stack((arr, arr))

        with self._lock:
            self._output_queue.append(arr)
            depth = len(self._output_queue)

        self.metrics.record_buffer_depth(input_depth=0, output_depth=depth)

    def clear(self) -> None:
        """Flush and clear output queue (used for barge-in / stop speaking)."""
        with self._lock:
            self._output_queue.clear()
            self._current_chunk = None
            self._current_offset = 0

        self.metrics.record_buffer_depth(input_depth=0, output_depth=0)
        logger.info("AudioOutputStream: Cleared playback queue.")

    def pause(self) -> None:
        """Pause playback stream."""
        with self._lock:
            if self._stream and self._state == AudioStreamState.RUNNING:
                self._stream.stop()
                self._state = AudioStreamState.PAUSED
                self.metrics.stop_output_timer()
                logger.info("AudioOutputStream: Paused stream.")

    def resume(self) -> None:
        """Resume playback stream."""
        with self._lock:
            if self._stream and self._state == AudioStreamState.PAUSED:
                self._stream.start()
                self._state = AudioStreamState.RUNNING
                self.metrics.start_output_timer()
                logger.info("AudioOutputStream: Resumed stream.")

    def stop(self) -> None:
        """Stop playback stream and clear queue."""
        self.clear()
        with self._lock:
            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"AudioOutputStream: Error closing stream: {exc}")
                finally:
                    self._stream = None

            self._state = AudioStreamState.STOPPED
            self.metrics.stop_output_timer()
            logger.info("AudioOutputStream: Stopped stream.")

    def _audio_callback(
        self,
        outdata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags,
    ) -> None:
        """Lightweight playback callback invoked by C sounddevice thread."""
        if status:
            logger.warning(f"AudioOutputStream: Callback status warning: {status}")

        filled_frames = 0
        channels = self.config.output_channels

        with self._lock:
            while filled_frames < frames:
                if self._current_chunk is None:
                    if not self._output_queue:
                        break
                    self._current_chunk = self._output_queue.popleft()
                    self._current_offset = 0

                chunk_len = len(self._current_chunk)
                remaining_chunk = chunk_len - self._current_offset
                needed_frames = frames - filled_frames

                take_frames = min(remaining_chunk, needed_frames)
                start_src = self._current_offset
                end_src = start_src + take_frames

                if channels == 1 and len(self._current_chunk.shape) > 1:
                    src_block = self._current_chunk[start_src:end_src, 0]
                else:
                    src_block = self._current_chunk[start_src:end_src]

                if channels == 2 and len(src_block.shape) == 1:
                    src_block = np.column_stack((src_block, src_block))

                outdata[filled_frames : filled_frames + take_frames] = src_block
                filled_frames += take_frames
                self._current_offset += take_frames

                if self._current_offset >= chunk_len:
                    self._current_chunk = None
                    self._current_offset = 0

        # Fill remaining buffer with silence if queue is empty
        if filled_frames < frames:
            outdata[filled_frames:] = 0.0

        if filled_frames > 0:
            self.metrics.record_output_frame(frame_sample_count=filled_frames)
