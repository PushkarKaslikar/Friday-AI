"""Diagnostic health and operational status provider for TTS Subsystem.

Phase 3.6 - Piper Local Text-to-Speech Engine
"""

from typing import Any

from app.voice.tts.metrics import TTSMetrics


class TTSDiagnostics:
    """Provides diagnostic health checks and metric snapshots for TTS Service."""

    def __init__(self, metrics: TTSMetrics | None = None) -> None:
        self.metrics = metrics or TTSMetrics()

    def get_health_report(
        self,
        service_state: str = "READY",
        voice_name: str = "en_US-amy-medium",
        model_loaded: bool = False,
        sample_rate: int = 22050,
        enabled: bool = True,
        auto_play: bool = True,
        is_speaking: bool = False,
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
            "provider": "Piper (piper-tts)",
            "service_state": service_state,
            "voice_name": voice_name,
            "model_loaded": model_loaded,
            "sample_rate": sample_rate,
            "enabled": enabled,
            "auto_play": auto_play,
            "is_speaking": is_speaking,
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
