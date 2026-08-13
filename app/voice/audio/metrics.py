"""Performance metrics collector for Audio Engine operations."""

import threading
import time
from typing import Any


class AudioMetrics:
    """Thread-safe performance & operational metrics collector for real-time audio streaming."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._input_frames_received: int = 0
        self._output_frames_played: int = 0
        self._input_buffer_depth: int = 0
        self._output_buffer_depth: int = 0
        self._buffer_overflow_count: int = 0
        self._dropped_frames_count: int = 0
        self._audio_errors_count: int = 0
        self._device_changes_count: int = 0
        self._device_reconnects_count: int = 0

        self._input_stream_start_time: float | None = None
        self._output_stream_start_time: float | None = None

        self._total_callback_time_ms: float = 0.0
        self._callback_count: int = 0
        self._max_callback_duration_ms: float = 0.0

    def record_input_frame(
        self, frame_sample_count: int, callback_duration_ms: float = 0.0
    ) -> None:
        """Record an incoming captured audio frame."""
        with self._lock:
            self._input_frames_received += 1
            if callback_duration_ms > 0:
                self._callback_count += 1
                self._total_callback_time_ms += callback_duration_ms
                self._max_callback_duration_ms = max(
                    self._max_callback_duration_ms, callback_duration_ms
                )

    def record_output_frame(self, frame_sample_count: int) -> None:
        """Record an outgoing played audio frame."""
        with self._lock:
            self._output_frames_played += 1

    def record_buffer_depth(self, input_depth: int, output_depth: int = 0) -> None:
        """Update active buffer utilization depth."""
        with self._lock:
            self._input_buffer_depth = input_depth
            self._output_buffer_depth = output_depth

    def record_overflow(self, dropped_count: int = 1) -> None:
        """Record a ring buffer overflow event."""
        with self._lock:
            self._buffer_overflow_count += 1
            self._dropped_frames_count += dropped_count

    def record_error(self) -> None:
        """Record an audio error occurrence."""
        with self._lock:
            self._audio_errors_count += 1

    def record_device_change(self) -> None:
        """Record a device selection change."""
        with self._lock:
            self._device_changes_count += 1

    def record_device_reconnect(self) -> None:
        """Record an automatic device reconnection."""
        with self._lock:
            self._device_reconnects_count += 1

    def start_input_timer(self) -> None:
        """Mark input stream start time."""
        with self._lock:
            self._input_stream_start_time = time.time()

    def stop_input_timer(self) -> None:
        """Reset input stream start time."""
        with self._lock:
            self._input_stream_start_time = None

    def start_output_timer(self) -> None:
        """Mark output stream start time."""
        with self._lock:
            self._output_stream_start_time = time.time()

    def stop_output_timer(self) -> None:
        """Reset output stream start time."""
        with self._lock:
            self._output_stream_start_time = None

    def snapshot(self) -> dict[str, Any]:
        """Generate a thread-safe snapshot dictionary of all current audio metrics."""
        with self._lock:
            avg_callback_ms = (
                round(self._total_callback_time_ms / self._callback_count, 3)
                if self._callback_count > 0
                else 0.0
            )

            input_uptime = (
                round(time.time() - self._input_stream_start_time, 2)
                if self._input_stream_start_time is not None
                else 0.0
            )
            output_uptime = (
                round(time.time() - self._output_stream_start_time, 2)
                if self._output_stream_start_time is not None
                else 0.0
            )

            return {
                "input_frames_received": self._input_frames_received,
                "output_frames_played": self._output_frames_played,
                "input_buffer_depth": self._input_buffer_depth,
                "output_buffer_depth": self._output_buffer_depth,
                "buffer_overflow_count": self._buffer_overflow_count,
                "dropped_frames": self._dropped_frames_count,
                "audio_errors": self._audio_errors_count,
                "device_changes": self._device_changes_count,
                "device_reconnects": self._device_reconnects_count,
                "input_stream_uptime_sec": input_uptime,
                "output_stream_uptime_sec": output_uptime,
                "average_callback_duration_ms": avg_callback_ms,
                "maximum_callback_duration_ms": round(
                    self._max_callback_duration_ms, 3
                ),
            }
