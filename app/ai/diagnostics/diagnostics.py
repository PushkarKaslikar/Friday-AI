"""Diagnostic health and status provider for Local LLM Runtime.

Phase 4.1 - Local LLM Runtime & Model Provider Foundation
"""

from typing import Any

from app.ai.metrics.metrics import LLMMetrics


class LLMDiagnostics:
    """Provides diagnostic health checks and metric snapshots for Local LLM Runtime."""

    def __init__(self, metrics: LLMMetrics | None = None) -> None:
        self.metrics = metrics or LLMMetrics()

    def get_health_report(
        self,
        provider_name: str = "llama_cpp",
        model_name: str = "Unknown",
        model_path: str = "",
        state: str = "UNINITIALIZED",
        device: str = "CPU",
        model_loaded: bool = False,
        context_size: int = 4096,
        supports_cuda: bool = False,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        """Format comprehensive diagnostic health report dictionary."""
        metrics_snapshot = self.metrics.get_metrics_snapshot()
        status = "HEALTHY" if model_loaded or state != "ERROR" else "DEGRADED"
        if state == "UNINITIALIZED" and not last_error:
            status = "UNINITIALIZED"

        return {
            "status": status,
            "provider": f"LocalLLM ({provider_name})",
            "provider_name": provider_name,
            "model_name": model_name,
            "model_path": model_path,
            "state": state,
            "device": device,
            "model_loaded": model_loaded,
            "context_size": context_size,
            "supports_cuda": supports_cuda,
            "last_error": last_error,
            "metrics": metrics_snapshot,
        }
