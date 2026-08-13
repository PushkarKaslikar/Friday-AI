"""Performance & operational metrics collector for Wake Word Subsystem."""

import threading
from typing import Any


class WakeWordMetrics:
    """Thread-safe operational metrics collector for wake word ONNX inference."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._analyzed_frames_count: int = 0
        self._inference_count: int = 0
        self._valid_detections_count: int = 0
        self._rejected_predictions_count: int = 0
        self._cooldown_suppressions_count: int = 0
        self._total_confidence_score_sum: float = 0.0
        self._total_inference_latency_ms: float = 0.0
        self._max_inference_latency_ms: float = 0.0
        self._detection_errors_count: int = 0

    def record_frame_analyzed(self) -> None:
        """Record an incoming AudioFrame."""
        with self._lock:
            self._analyzed_frames_count += 1

    def record_inference(self, latency_ms: float) -> None:
        """Record an ONNX model inference execution."""
        with self._lock:
            self._inference_count += 1
            self._total_inference_latency_ms += latency_ms
            self._max_inference_latency_ms = max(
                self._max_inference_latency_ms, latency_ms
            )

    def record_detection(self, score: float) -> None:
        """Record a validated wake word detection."""
        with self._lock:
            self._valid_detections_count += 1
            self._total_confidence_score_sum += score

    def record_rejected_prediction(self) -> None:
        """Record a prediction score below threshold."""
        with self._lock:
            self._rejected_predictions_count += 1

    def record_cooldown_suppression(self) -> None:
        """Record a prediction score suppressed during refractory cooldown."""
        with self._lock:
            self._cooldown_suppressions_count += 1

    def record_error(self) -> None:
        """Record a detection error."""
        with self._lock:
            self._detection_errors_count += 1

    def snapshot(self) -> dict[str, Any]:
        """Generate a thread-safe snapshot of wake word metrics."""
        with self._lock:
            avg_latency = (
                round(self._total_inference_latency_ms / self._inference_count, 3)
                if self._inference_count > 0
                else 0.0
            )
            avg_score = (
                round(
                    self._total_confidence_score_sum / self._valid_detections_count, 3
                )
                if self._valid_detections_count > 0
                else 0.0
            )

            return {
                "analyzed_frames_count": self._analyzed_frames_count,
                "inference_count": self._inference_count,
                "valid_detections_count": self._valid_detections_count,
                "rejected_predictions_count": self._rejected_predictions_count,
                "cooldown_suppressions_count": self._cooldown_suppressions_count,
                "average_inference_latency_ms": avg_latency,
                "maximum_inference_latency_ms": round(
                    self._max_inference_latency_ms, 3
                ),
                "average_detection_score": avg_score,
                "detection_errors_count": self._detection_errors_count,
            }
