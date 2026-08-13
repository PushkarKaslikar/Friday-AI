"""Unit tests for SchedulerService."""

import time

from app.services.scheduler.scheduler_service import SchedulerService


def test_scheduler_service_interval():
    ss = SchedulerService()
    ss.initialize()
    ss.start()

    counts = []

    def job_fn():
        counts.append(1)

    added = ss.add_interval_job("job_1", job_fn, seconds=1)
    assert added is True

    time.sleep(1.5)
    assert len(counts) >= 1

    removed = ss.remove_job("job_1")
    assert removed is True

    ss.stop()
