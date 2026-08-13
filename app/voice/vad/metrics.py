"""Operational metrics tracking for Voice Activity Detection.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VADMetrics:
    """Thread-safe operational metrics collector for VAD detector."""

    frames_processed: int = 0
    speech_frames: int = 0
    non_speech_frames: int = 0
    speech_started_count: int = 0
    speech_stopped_count: int = 0
    false_start_candidates: int = 0
    silence_candidates: int = 0
    total_inference_latency_ms: float = 0.0
    max_inference_latency_ms: float = 0.0
    peak_speech_probability: float = 0.0
    total_speech_probability: float = 0.0
    total_speech_duration_seconds: float = 0.0
    total_silence_duration_seconds: float = 0.0
    errors_count: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record_frame(self, probability: float, latency_ms: float) -> None:
        """Record inference statistics for a single audio frame."""
        with self._lock:
            self.frames_processed += 1
            if probability >= 0.5:
                self.speech_frames += 1
            else:
                self.non_speech_frames += 1

            self.total_speech_probability += probability
            self.peak_speech_probability = max(
                self.peak_speech_probability, probability
            )

            self.total_inference_latency_ms += latency_ms
            self.max_inference_latency_ms = max(
                self.max_inference_latency_ms, latency_ms
            )

    def record_speech_started(self) -> None:
        """Record SpeechStarted event."""
        with self._lock:
            self.speech_started_count += 1

    def record_speech_stopped(
        self, duration_seconds: float, silence_seconds: float
    ) -> None:
        """Record SpeechStopped event with timing statistics."""
        with self._lock:
            self.speech_stopped_count += 1
            self.total_speech_duration_seconds += duration_seconds
            self.total_silence_duration_seconds += silence_seconds

    def record_false_start(self) -> None:
        """Record false start candidate reset."""
        with self._lock:
            self.false_start_candidates += 1

    def record_silence_candidate(self) -> None:
        """Record silence candidate transition."""
        with self._lock:
            self.silence_candidates += 1

    def record_error(self) -> None:
        """Record VAD error."""
        with self._lock:
            self.errors_count += 1

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary summary."""
        with self._lock:
            avg_latency = (
                self.total_inference_latency_ms / self.frames_processed
                if self.frames_processed > 0
                else 0.0
            )
            avg_prob = (
                self.total_speech_probability / self.frames_processed
                if self.frames_processed > 0
                else 0.0
            )
            avg_dur = (
                self.total_speech_duration_seconds / self.speech_stopped_count
                if self.speech_stopped_count > 0
                else 0.0
            )
            return {
                "frames_processed": self.frames_processed,
                "speech_frames": self.speech_frames,
                "non_speech_frames": self.non_speech_frames,
                "speech_started_count": self.speech_started_count,
                "speech_stopped_count": self.speech_stopped_count,
                "false_start_candidates": self.false_start_candidates,
                "silence_candidates": self.silence_candidates,
                "average_inference_latency_ms": round(avg_latency, 3),
                "max_inference_latency_ms": round(self.max_inference_latency_ms, 3),
                "average_speech_probability": round(avg_prob, 3),
                "peak_speech_probability": round(self.peak_speech_probability, 3),
                "average_speech_duration_seconds": round(avg_dur, 3),
                "errors_count": self.errors_count,
            }

    def reset(self) -> None:
        """Reset all metrics counters."""
        with self._lock:
            self.frames_processed = 0
            self.speech_frames = 0
            self.non_speech_frames = 0
            self.speech_started_count = 0
            self.speech_stopped_count = 0
            self.false_start_candidates = 0
            self.silence_candidates = 0
            self.total_inference_latency_ms = 0.0
            self.max_inference_latency_ms = 0.0
            self.peak_speech_probability = 0.0
            self.total_speech_probability = 0.0
            self.total_speech_duration_seconds = 0.0
            self.total_silence_duration_seconds = 0.0
            self.errors_count = 0
