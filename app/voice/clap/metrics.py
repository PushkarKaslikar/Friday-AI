"""Performance & operational metrics collector for Double-Clap Detection Subsystem."""

import threading
from typing import Any


class ClapMetrics:
    """Thread-safe performance & operational metrics collector for clap signal processing."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._analyzed_frames_count: int = 0
        self._candidate_transients_count: int = 0
        self._valid_claps_count: int = 0
        self._rejected_candidates_count: int = 0
        self._double_clap_attempts_count: int = 0
        self._successful_double_claps_count: int = 0
        self._timed_out_claps_count: int = 0
        self._cooldown_suppressions_count: int = 0
        self._total_confidence_sum: float = 0.0
        self._total_detection_latency_ms: float = 0.0
        self._detection_errors_count: int = 0

    def record_frame_analyzed(self) -> None:
        """Record an analyzed AudioFrame."""
        with self._lock:
            self._analyzed_frames_count += 1

    def record_candidate(self) -> None:
        """Record a candidate impulse transient."""
        with self._lock:
            self._candidate_transients_count += 1

    def record_valid_clap(self, confidence: float, latency_ms: float = 0.0) -> None:
        """Record a validated single clap."""
        with self._lock:
            self._valid_claps_count += 1
            self._total_confidence_sum += confidence
            self._total_detection_latency_ms += latency_ms

    def record_rejected_candidate(self) -> None:
        """Record a rejected non-clap candidate transient."""
        with self._lock:
            self._rejected_candidates_count += 1

    def record_double_clap_attempt(self) -> None:
        """Record a candidate second clap attempt."""
        with self._lock:
            self._double_clap_attempts_count += 1

    def record_successful_double_clap(self) -> None:
        """Record a successful double-clap gesture activation."""
        with self._lock:
            self._successful_double_claps_count += 1

    def record_timeout(self) -> None:
        """Record a single clap timing window timeout."""
        with self._lock:
            self._timed_out_claps_count += 1

    def record_cooldown_suppression(self) -> None:
        """Record a candidate clap suppressed during refractory cooldown."""
        with self._lock:
            self._cooldown_suppressions_count += 1

    def record_error(self) -> None:
        """Record a detection error."""
        with self._lock:
            self._detection_errors_count += 1

    def snapshot(self) -> dict[str, Any]:
        """Generate a thread-safe snapshot dictionary of clap detection metrics."""
        with self._lock:
            avg_confidence = (
                round(self._total_confidence_sum / self._valid_claps_count, 3)
                if self._valid_claps_count > 0
                else 0.0
            )
            avg_latency = (
                round(self._total_detection_latency_ms / self._valid_claps_count, 3)
                if self._valid_claps_count > 0
                else 0.0
            )

            return {
                "analyzed_frames_count": self._analyzed_frames_count,
                "candidate_transients_count": self._candidate_transients_count,
                "valid_claps_count": self._valid_claps_count,
                "rejected_candidates_count": self._rejected_candidates_count,
                "double_clap_attempts_count": self._double_clap_attempts_count,
                "successful_double_claps_count": self._successful_double_claps_count,
                "timed_out_claps_count": self._timed_out_claps_count,
                "cooldown_suppressions_count": self._cooldown_suppressions_count,
                "average_clap_confidence": avg_confidence,
                "average_detection_latency_ms": avg_latency,
                "detection_errors_count": self._detection_errors_count,
            }
