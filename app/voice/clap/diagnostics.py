"""Diagnostic health report formatting for Double-Clap Detection Subsystem."""

from typing import Any

from app.voice.clap.metrics import ClapMetrics
from app.voice.clap.models import ClapConfiguration, ClapState


class ClapDiagnostics:
    """Formats diagnostic health reports for ClapDetector service and metrics."""

    def __init__(self, metrics: ClapMetrics | None = None) -> None:
        self.metrics = metrics or ClapMetrics()

    def get_health_report(
        self,
        detector_state: ClapState,
        enabled: bool,
        config: ClapConfiguration,
        noise_floor_energy: float,
        last_clap_timestamp: float | None = None,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured diagnostic report for CLI and SystemDiagnostics service."""
        metrics_snapshot = self.metrics.snapshot()

        return {
            "status": (
                "HEALTHY"
                if enabled and detector_state != ClapState.ERROR
                else "DEGRADED"
            ),
            "state": detector_state.value,
            "enabled": enabled,
            "noise_floor_energy": round(noise_floor_energy, 6),
            "last_clap_timestamp": last_clap_timestamp or 0.0,
            "min_clap_interval_ms": config.min_clap_interval_ms,
            "max_clap_interval_ms": config.max_clap_interval_ms,
            "cooldown_ms": config.cooldown_ms,
            "energy_threshold_multiplier": config.energy_threshold_multiplier,
            "min_peak_amplitude": config.min_peak_amplitude,
            "last_error": last_error or "None",
            "metrics": metrics_snapshot,
        }
