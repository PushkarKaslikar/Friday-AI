"""Unit tests for CrashHandler."""

import sys
from pathlib import Path

from app.crash.crash_handler import CrashHandler
from app.utilities.file_utils import read_json_file


def test_crash_handler_report_generation(tmp_path: Path):
    report_dir = tmp_path / "crash_reports"
    ch = CrashHandler(report_dir=report_dir)

    try:
        raise ValueError("Simulated crash error")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()
        report_file = ch.generate_crash_report(exc_type, exc_value, exc_tb)

    assert report_file.exists()
    data = read_json_file(report_file)
    assert data["exception"]["type"] == "ValueError"
    assert "Simulated crash error" in data["exception"]["message"]
