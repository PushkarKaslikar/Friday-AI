"""Operational performance metrics for Text-to-Speech (TTS) Subsystem.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

import threading
from typing import Any

import numpy as np


class TTSMetrics:
    """Thread-safe collector for TTS operational performance metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._synthesis_requests_total: int = 0
        self._successful_synthesis: int = 0
        self._failed_synthesis: int = 0
        self._cancelled_requests: int = 0
        self._playback_completed: int = 0
        self._playback_stopped: int = 0
        self._total_audio_duration_sec: float = 0.0
        self._total_synthesis_time_sec: float = 0.0
        self._errors_count: int = 0
        self._synthesis_times_ms: list[float] = []

    def record_synthesis(
        self,
        status: str,
        audio_duration_sec: float,
        synthesis_time_sec: float,
    ) -> None:
        """Record details of a completed synthesis attempt."""
        with self._lock:
            self._synthesis_requests_total += 1
            synth_ms = synthesis_time_sec * 1000.0
            self._synthesis_times_ms.append(synth_ms)
            if len(self._synthesis_times_ms) > 1000:
                self._synthesis_times_ms.pop(0)

            self._total_audio_duration_sec += audio_duration_sec
            self._total_synthesis_time_sec += synthesis_time_sec

            if status == "SUCCESS":
                self._successful_synthesis += 1
            elif status == "FAILED":
                self._failed_synthesis += 1
                self._errors_count += 1
            elif status == "CANCELLED":
                self._cancelled_requests += 1

    def record_playback_completed(self) -> None:
        """Record a completed audio playback."""
        with self._lock:
            self._playback_completed += 1

    def record_playback_stopped(self) -> None:
        """Record an interrupted/stopped audio playback."""
        with self._lock:
            self._playback_stopped += 1

    def record_error(self) -> None:
        """Record an operational error."""
        with self._lock:
            self._errors_count += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe snapshot of all collected metrics."""
        with self._lock:
            avg_synth_ms = (
                (
                    self._total_synthesis_time_sec
                    / max(1, self._synthesis_requests_total)
                )
                * 1000.0
                if self._synthesis_requests_total > 0
                else 0.0
            )
            avg_rtf = (
                self._total_synthesis_time_sec
                / max(0.001, self._total_audio_duration_sec)
                if self._total_audio_duration_sec > 0
                else 0.0
            )

            p50_ms = 0.0
            p95_ms = 0.0
            if self._synthesis_times_ms:
                arr = np.array(self._synthesis_times_ms)
                p50_ms = round(float(np.percentile(arr, 50)), 2)
                p95_ms = round(float(np.percentile(arr, 95)), 2)

            return {
                "synthesis_requests_total": self._synthesis_requests_total,
                "successful_synthesis": self._successful_synthesis,
                "failed_synthesis": self._failed_synthesis,
                "cancelled_requests": self._cancelled_requests,
                "playback_completed": self._playback_completed,
                "playback_stopped": self._playback_stopped,
                "total_audio_duration_seconds": round(
                    self._total_audio_duration_sec, 2
                ),
                "total_synthesis_time_seconds": round(
                    self._total_synthesis_time_sec, 2
                ),
                "average_synthesis_time_ms": round(avg_synth_ms, 2),
                "average_real_time_factor": round(avg_rtf, 3),
                "p50_synthesis_time_ms": p50_ms,
                "p95_synthesis_time_ms": p95_ms,
                "errors_count": self._errors_count,
            }

    def reset(self) -> None:
        """Reset all metrics counters."""
        with self._lock:
            self._synthesis_requests_total = 0
            self._successful_synthesis = 0
            self._failed_synthesis = 0
            self._cancelled_requests = 0
            self._playback_completed = 0
            self._playback_stopped = 0
            self._total_audio_duration_sec = 0.0
            self._total_synthesis_time_sec = 0.0
            self._errors_count = 0
            self._synthesis_times_ms.clear()
