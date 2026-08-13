"""Unit tests for ThreadManager and BaseWorker."""

import time

from app.services.threading.thread_manager import ThreadManager
from app.services.workers.base_worker import BaseWorker


class SampleWorker(BaseWorker[int]):
    """Sample worker implementation."""

    def run(self) -> int:
        self.report_progress(50, "Halfway")
        return 100


def test_thread_manager_task():
    tm = ThreadManager()
    results = []

    def task():
        return 42

    future = tm.submit_task("t1", task, callback=lambda r: results.append(r))
    val = future.result(timeout=2.0)
    assert val == 42
    time.sleep(0.05)
    assert results == [42]


def test_base_worker():
    progresses = []
    successes = []

    worker = SampleWorker(
        worker_id="w1",
        on_progress=lambda p, m: progresses.append((p, m)),
        on_success=lambda r: successes.append(r),
    )

    res = worker.execute()
    assert res == 100
    assert len(progresses) == 1
    assert progresses[0] == (50, "Halfway")
    assert successes == [100]
