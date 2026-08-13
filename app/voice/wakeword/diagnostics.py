"""Diagnostic health report formatting for Wake Word Subsystem."""

from typing import Any

from app.voice.wakeword.metrics import WakeWordMetrics
from app.voice.wakeword.models import WakeWordConfiguration, WakeWordState


class WakeWordDiagnostics:
    """Formats diagnostic health reports for WakeWordDetector service."""

    def __init__(self, metrics: WakeWordMetrics | None = None) -> None:
        self.metrics = metrics or WakeWordMetrics()

    def get_health_report(
        self,
        detector_state: WakeWordState,
        enabled: bool,
        config: WakeWordConfiguration,
        active_model_name: str,
        model_path: str,
        is_model_loaded: bool,
        is_custom_friday_model: bool,
        last_detection_timestamp: float | None = None,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured diagnostic report for CLI and SystemDiagnostics service."""
        metrics_snapshot = self.metrics.snapshot()

        status = (
            "HEALTHY"
            if enabled and is_model_loaded and detector_state != WakeWordState.ERROR
            else "DEGRADED"
        )

        return {
            "status": status,
            "state": detector_state.value,
            "enabled": enabled,
            "provider": "OpenWakeWord",
            "wake_word": config.model_name,
            "active_model_name": active_model_name,
            "model_path": model_path,
            "is_model_loaded": is_model_loaded,
            "is_custom_friday_model": is_custom_friday_model,
            "threshold": config.threshold,
            "cooldown_ms": config.cooldown_ms,
            "last_detection_timestamp": last_detection_timestamp or 0.0,
            "last_error": last_error or "None",
            "metrics": metrics_snapshot,
        }
