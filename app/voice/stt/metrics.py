"""Operational performance metrics for Speech-to-Text (STT) Subsystem.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

import threading
from typing import Any

import numpy as np


class STTMetrics:
    """Thread-safe collector for STT operational performance metrics."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._transcriptions_total: int = 0
        self._successful_transcriptions: int = 0
        self._failed_transcriptions: int = 0
        self._empty_transcriptions: int = 0
        self._cancelled_transcriptions: int = 0
        self._total_audio_duration_sec: float = 0.0
        self._total_processing_time_sec: float = 0.0
        self._characters_transcribed: int = 0
        self._words_transcribed: int = 0
        self._errors_count: int = 0
        self._processing_times_ms: list[float] = []

    def record_transcription(
        self,
        status: str,
        audio_duration_sec: float,
        processing_time_sec: float,
        text: str = "",
    ) -> None:
        """Record details of a completed transcription attempt."""
        with self._lock:
            self._transcriptions_total += 1
            proc_ms = processing_time_sec * 1000.0
            self._processing_times_ms.append(proc_ms)
            if len(self._processing_times_ms) > 1000:
                self._processing_times_ms.pop(0)

            self._total_audio_duration_sec += audio_duration_sec
            self._total_processing_time_sec += processing_time_sec

            if status == "SUCCESS":
                self._successful_transcriptions += 1
                clean_text = text.strip()
                self._characters_transcribed += len(clean_text)
                if clean_text:
                    self._words_transcribed += len(clean_text.split())
            elif status == "EMPTY":
                self._empty_transcriptions += 1
            elif status == "FAILED":
                self._failed_transcriptions += 1
                self._errors_count += 1
            elif status == "CANCELLED":
                self._cancelled_transcriptions += 1

    def record_error(self) -> None:
        """Record an operational error."""
        with self._lock:
            self._errors_count += 1

    def get_metrics_snapshot(self) -> dict[str, Any]:
        """Return thread-safe snapshot of all collected metrics."""
        with self._lock:
            avg_proc_ms = (
                (self._total_processing_time_sec / max(1, self._transcriptions_total))
                * 1000.0
                if self._transcriptions_total > 0
                else 0.0
            )
            avg_rtf = (
                self._total_processing_time_sec
                / max(0.001, self._total_audio_duration_sec)
                if self._total_audio_duration_sec > 0
                else 0.0
            )

            p50_ms = 0.0
            p95_ms = 0.0
            if self._processing_times_ms:
                arr = np.array(self._processing_times_ms)
                p50_ms = round(float(np.percentile(arr, 50)), 2)
                p95_ms = round(float(np.percentile(arr, 95)), 2)

            return {
                "transcriptions_total": self._transcriptions_total,
                "successful_transcriptions": self._successful_transcriptions,
                "failed_transcriptions": self._failed_transcriptions,
                "empty_transcriptions": self._empty_transcriptions,
                "cancelled_transcriptions": self._cancelled_transcriptions,
                "total_audio_duration_seconds": round(
                    self._total_audio_duration_sec, 2
                ),
                "total_processing_time_seconds": round(
                    self._total_processing_time_sec, 2
                ),
                "average_processing_time_ms": round(avg_proc_ms, 2),
                "average_real_time_factor": round(avg_rtf, 3),
                "p50_processing_time_ms": p50_ms,
                "p95_processing_time_ms": p95_ms,
                "characters_transcribed": self._characters_transcribed,
                "words_transcribed": self._words_transcribed,
                "errors_count": self._errors_count,
            }

    def reset(self) -> None:
        """Reset all metrics counters."""
        with self._lock:
            self._transcriptions_total = 0
            self._successful_transcriptions = 0
            self._failed_transcriptions = 0
            self._empty_transcriptions = 0
            self._cancelled_transcriptions = 0
            self._total_audio_duration_sec = 0.0
            self._total_processing_time_sec = 0.0
            self._characters_transcribed = 0
            self._words_transcribed = 0
            self._errors_count = 0
            self._processing_times_ms.clear()
