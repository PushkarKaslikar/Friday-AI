"""Thread-safe bounded ring buffer for real-time AudioFrame streaming."""

import collections
import threading

from app.voice.audio.metrics import AudioMetrics
from app.voice.audio.models import AudioFrame


class AudioRingBuffer:
    """Bounded thread-safe ring buffer supporting continuous streaming and low-latency frame delivery.

    Backpressure Policy: Drop oldest frames when max capacity is reached.
    This preserves low-latency real-time processing for downstream consumers (Clap, Wake Word, VAD).
    """

    def __init__(
        self,
        max_capacity_frames: int = 150,  # ~5 seconds of 32ms frames
        metrics: AudioMetrics | None = None,
    ) -> None:
        self.max_capacity_frames = max_capacity_frames
        self.metrics = metrics
        self._buffer: collections.deque[AudioFrame] = collections.deque(
            maxlen=max_capacity_frames
        )
        self._lock = threading.Lock()

    @property
    def capacity(self) -> int:
        """Maximum frame capacity of ring buffer."""
        return self.max_capacity_frames

    @property
    def size(self) -> int:
        """Current number of AudioFrames in buffer."""
        with self._lock:
            return len(self._buffer)

    @property
    def is_empty(self) -> bool:
        """Check if buffer contains no frames."""
        with self._lock:
            return len(self._buffer) == 0

    @property
    def is_full(self) -> bool:
        """Check if buffer has reached maximum capacity."""
        with self._lock:
            return len(self._buffer) >= self.max_capacity_frames

    def push(self, frame: AudioFrame) -> bool:
        """Push a new AudioFrame into the buffer.

        If buffer is full, drops the oldest frame (FIFO backpressure policy)
        and records overflow metrics.
        """
        with self._lock:
            was_full = len(self._buffer) >= self.max_capacity_frames
            if was_full and self.metrics:
                self.metrics.record_overflow(dropped_count=1)

            self._buffer.append(frame)
            current_len = len(self._buffer)

        if self.metrics:
            self.metrics.record_buffer_depth(input_depth=current_len)

        return not was_full

    def pop(self) -> AudioFrame | None:
        """Remove and return the oldest AudioFrame from the buffer."""
        with self._lock:
            if not self._buffer:
                return None
            frame = self._buffer.popleft()
            current_len = len(self._buffer)

        if self.metrics:
            self.metrics.record_buffer_depth(input_depth=current_len)

        return frame

    def peek(self) -> AudioFrame | None:
        """Return the oldest AudioFrame without removing it."""
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[0]

    def get_all(self) -> list[AudioFrame]:
        """Return a copy of all current frames in chronological order."""
        with self._lock:
            return list(self._buffer)

    def clear(self) -> None:
        """Flush and clear all frames in buffer."""
        with self._lock:
            self._buffer.clear()
        if self.metrics:
            self.metrics.record_buffer_depth(input_depth=0)
