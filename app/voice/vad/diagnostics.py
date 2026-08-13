"""Diagnostic health reporting for Voice Activity Detection.

Phase 3.4 - Voice Activity Detection & Speech Boundary Engine
"""

from typing import Any

from app.voice.vad.metrics import VADMetrics
from app.voice.vad.models import VADConfiguration, VADState


class VADDiagnostics:
    """Formatter for VAD health reports and diagnostic data."""

    def __init__(self, config: VADConfiguration, metrics: VADMetrics) -> None:
        self.config = config
        self.metrics = metrics

    def generate_health_report(
        self,
        current_state: VADState,
        is_model_loaded: bool,
        is_listening: bool,
        model_path: str = "",
    ) -> dict[str, Any]:
        """Generate structured diagnostic health report."""
        status = (
            "HEALTHY"
            if is_model_loaded and current_state != VADState.ERROR
            else ("DISABLED" if not self.config.enabled else "UNHEALTHY")
        )

        return {
            "status": status,
            "provider": "Silero VAD (ONNX Runtime)",
            "model_name": self.config.model_name,
            "model_path": model_path,
            "is_model_loaded": is_model_loaded,
            "is_listening": is_listening,
            "current_state": current_state.value,
            "enabled": self.config.enabled,
            "sample_rate": self.config.sample_rate,
            "speech_threshold": self.config.speech_threshold,
            "negative_threshold": self.config.negative_threshold,
            "speech_start_confirmation_ms": self.config.speech_start_confirmation_ms,
            "min_silence_duration_ms": self.config.min_silence_duration_ms,
            "speech_pad_ms": self.config.speech_pad_ms,
            "metrics": self.metrics.to_dict(),
        }

    def format_cli_summary(
        self,
        current_state: VADState,
        is_model_loaded: bool,
        is_listening: bool,
        model_path: str = "",
    ) -> str:
        """Format CLI human-readable health check report string."""
        report = self.generate_health_report(
            current_state, is_model_loaded, is_listening, model_path
        )
        m = report["metrics"]

        lines = [
            "========================================",
            "FRIDAY VAD HEALTH CHECK",
            "========================================",
            f"Detector Status:         {report['status']}",
            f"Provider:                {report['provider']}",
            f"Model Name:              {report['model_name']}",
            f"Model Path:              {report['model_path']}",
            f"Model Loaded:            {report['is_model_loaded']}",
            f"Listening:               {report['is_listening']}",
            f"State:                   {report['current_state']}",
            f"Enabled:                 {report['enabled']}",
            f"Sample Rate:             {report['sample_rate']} Hz",
            f"Speech Threshold:        {report['speech_threshold']}",
            f"Negative Threshold:      {report['negative_threshold']}",
            f"Speech Confirmation:     {report['speech_start_confirmation_ms']} ms",
            f"Min Silence Duration:    {report['min_silence_duration_ms']} ms",
            f"Speech Padding:          {report['speech_pad_ms']} ms",
            "----------------------------------------",
            "OPERATIONAL METRICS:",
            f"  Frames Processed:      {m['frames_processed']}",
            f"  Speech Frames:         {m['speech_frames']}",
            f"  Non-Speech Frames:     {m['non_speech_frames']}",
            f"  Speech Started Count:  {m['speech_started_count']}",
            f"  Speech Stopped Count:  {m['speech_stopped_count']}",
            f"  False Start Candidates:{m['false_start_candidates']}",
            f"  Avg Inference Latency: {m['average_inference_latency_ms']} ms",
            f"  Max Inference Latency: {m['max_inference_latency_ms']} ms",
            f"  Peak Speech Prob:      {m['peak_speech_probability']}",
            f"  Errors Count:          {m['errors_count']}",
            "========================================",
        ]
        return "\n".join(lines)
