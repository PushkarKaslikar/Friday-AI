"""Thread-safe bounded PCM audio frame collector for Speech-to-Text.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

import threading

import numpy as np

from app.logging import logger
from app.voice.audio.models import AudioFrame


class SpeechSegmentBuffer:
    """Bounded, thread-safe in-memory PCM audio frame buffer.

    Collects float32 audio frames between SpeechStarted and SpeechStopped events.
    Enforces maximum duration (default: 30 seconds) to prevent unbounded memory growth.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        max_duration_seconds: float = 30.0,
    ) -> None:
        self.sample_rate = sample_rate
        self.max_duration_seconds = max_duration_seconds
        self.max_samples = int(sample_rate * max_duration_seconds)

        self._frames: list[np.ndarray] = []
        self._total_samples: int = 0
        self._is_collecting: bool = False
        self._lock = threading.Lock()

    @property
    def is_collecting(self) -> bool:
        """Check if buffer is actively recording frames."""
        with self._lock:
            return self._is_collecting

    @property
    def duration_seconds(self) -> float:
        """Current duration of collected audio in seconds."""
        with self._lock:
            return round(self._total_samples / max(1, self.sample_rate), 3)

    def start_collection(self) -> None:
        """Clear existing buffer and mark active collection mode."""
        with self._lock:
            self._frames.clear()
            self._total_samples = 0
            self._is_collecting = True
            logger.debug("SpeechSegmentBuffer: Started audio collection.")

    def push_frame(self, frame: AudioFrame) -> bool:
        """Append AudioFrame samples to collection buffer.

        Args:
            frame: AudioFrame from AudioEngine

        Returns:
            bool: True if frame added, False if limit exceeded or not collecting.
        """
        with self._lock:
            if not self._is_collecting:
                return False

            samples = frame.samples
            if not isinstance(samples, np.ndarray):
                samples = np.array(samples, dtype=np.float32)
            elif samples.dtype != np.float32:
                samples = samples.astype(np.float32)

            if samples.ndim > 1:
                samples = samples.squeeze()

            n_samples = len(samples)
            if self._total_samples + n_samples > self.max_samples:
                logger.warning(
                    f"SpeechSegmentBuffer: Max duration ({self.max_duration_seconds}s) reached. Frame capped."
                )
                allowed = max(0, self.max_samples - self._total_samples)
                if allowed > 0:
                    self._frames.append(samples[:allowed])
                    self._total_samples += allowed
                return False

            self._frames.append(samples)
            self._total_samples += n_samples
            return True

    def finalize(self) -> tuple[np.ndarray, float]:
        """Finalize collection and return combined float32 audio array and duration in seconds."""
        with self._lock:
            self._is_collecting = False
            if not self._frames:
                combined = np.zeros(0, dtype=np.float32)
                duration = 0.0
            else:
                combined = np.concatenate(self._frames, axis=0).astype(np.float32)
                duration = round(len(combined) / max(1, self.sample_rate), 3)

            self._frames.clear()
            self._total_samples = 0
            logger.debug(
                f"SpeechSegmentBuffer: Finalized segment ({duration}s, {len(combined)} samples)."
            )
            return combined, duration

    def clear(self) -> None:
        """Reset buffer state without returning audio."""
        with self._lock:
            self._frames.clear()
            self._total_samples = 0
            self._is_collecting = False
