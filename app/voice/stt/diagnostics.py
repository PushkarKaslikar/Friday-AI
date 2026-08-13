"""Diagnostic health and operational status provider for STT Subsystem.

Phase 3.5 - Faster-Whisper Speech-to-Text Engine
"""

from typing import Any

from app.voice.stt.metrics import STTMetrics


class STTDiagnostics:
    """Provides diagnostic health checks and metric snapshots for STT Service."""

    def __init__(self, metrics: STTMetrics | None = None) -> None:
        self.metrics = metrics or STTMetrics()

    def get_health_report(
        self,
        service_state: str = "READY",
        model_name: str = "base",
        model_loaded: bool = False,
        device: str = "cpu",
        compute_type: str = "int8",
        listening: bool = True,
        enabled: bool = True,
        language: str | None = None,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Format comprehensive diagnostic health report dictionary."""
        metrics_snapshot = self.metrics.get_metrics_snapshot()
        status = "HEALTHY"
        if not enabled:
            status = "DISABLED"
        elif not model_loaded or last_error:
            status = "DEGRADED"

        return {
            "status": status,
            "provider": "Faster-Whisper (ctranslate2)",
            "service_state": service_state,
            "model_name": model_name,
            "model_loaded": model_loaded,
            "device": device,
            "compute_type": compute_type,
            "listening": listening,
            "enabled": enabled,
            "language": language or "auto",
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
