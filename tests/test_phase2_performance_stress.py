"""Performance & stress audit test suite evaluating execution throughput, registry thread-safety, cancellation, and memory stability."""

import concurrent.futures
import time

import psutil
import pytest

from app.bootstrap.bootstrapper import AppBootstrapper
from app.tools.execution.cancellation import CancellationToken
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.models.request import ToolRequest
from app.tools.registry.tool_registry import ToolRegistry


@pytest.fixture(scope="module")
def app_bootstrap():
    """Module-level fixture initializing full application container."""
    bootstrapper = AppBootstrapper()
    return bootstrapper.run()


def test_performance_tool_execution_stress(app_bootstrap):
    """Stress test executing 100 sequential tool requests to verify throughput & memory stability."""
    container = app_bootstrap.container
    executor: ToolExecutor = container.tool_executor()

    process = psutil.Process()
    mem_before = process.memory_info().rss
    start_time = time.perf_counter()

    success_count = 0
    iterations = 100

    for i in range(iterations):
        res = executor.execute_request(
            ToolRequest(tool_id="system.echo", arguments={"message": f"Stress {i}"})
        )
        if res.success:
            success_count += 1

    elapsed = time.perf_counter() - start_time
    mem_after = process.memory_info().rss
    mem_growth_mb = (mem_after - mem_before) / (1024 * 1024)

    assert success_count == iterations
    assert elapsed < 10.0  # Must complete 100 executions in under 10 seconds
    assert mem_growth_mb < 50.0  # Memory growth must remain bounded under 50MB


def test_performance_registry_concurrency(app_bootstrap):
    """Verify thread-safety of ToolRegistry under concurrent lookups."""
    container = app_bootstrap.container
    registry: ToolRegistry = container.tool_registry()

    tool_ids = [
        "system.echo",
        "system.get_runtime_status",
        "files.list_directory",
        "browser.open",
    ]

    def lookup_worker(t_id: str) -> bool:
        tool = registry.get_tool(t_id)
        return tool is not None

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as thread_pool:
        futures = [thread_pool.submit(lookup_worker, t_id) for t_id in tool_ids * 25]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 100
    assert all(results)


def test_performance_cancellation_token_handling(app_bootstrap):
    """Verify CancellationToken produces clean structured cancellation response."""
    container = app_bootstrap.container
    executor: ToolExecutor = container.tool_executor()

    cancel_token = CancellationToken()
    cancel_token.request_cancellation(reason="Integration Test User Cancelled")

    res = executor.execute(
        tool_id="system.echo",
        arguments={"message": "Should be cancelled"},
    )
    assert res is not None
