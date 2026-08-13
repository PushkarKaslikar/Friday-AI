"""Unit tests for PerformanceMonitor."""

from app.monitoring.performance_monitor import PerformanceMonitor


def test_performance_monitor_metrics():
    pm = PerformanceMonitor()
    pm.initialize()
    pm.start()

    metrics = pm.get_metrics()
    assert "ram_usage_mb" in metrics
    assert "cpu_percent" in metrics
    assert "thread_count" in metrics
    assert metrics["ram_usage_mb"] > 0

    pm.stop()
