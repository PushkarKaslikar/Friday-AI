"""Diagnostic health report formatting for Audio Engine Subsystem."""

from typing import Any

from app.voice.audio.metrics import AudioMetrics


class AudioDiagnostics:
    """Formats diagnostic health reports for AudioEngine, device status, and stream metrics."""

    def __init__(self, metrics: AudioMetrics | None = None) -> None:
        self.metrics = metrics or AudioMetrics()

    def get_health_report(
        self,
        engine_state: str,
        input_state: str,
        output_state: str,
        active_input_device: str,
        active_output_device: str,
        sample_rate: int,
        channels: int,
        buffer_capacity_sec: float,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Generate structured diagnostic report for CLI and SystemDiagnostics service."""
        metrics_snapshot = self.metrics.snapshot()

        return {
            "status": "HEALTHY" if engine_state in ("READY", "RUNNING") else "DEGRADED",
            "engine_state": engine_state,
            "input_stream_state": input_state,
            "output_stream_state": output_state,
            "active_input_device": active_input_device,
            "active_output_device": active_output_device,
            "sample_rate_hz": sample_rate,
            "input_channels": channels,
            "buffer_capacity_seconds": buffer_capacity_sec,
            "last_error": last_error or "None",
            "metrics": metrics_snapshot,
        }
