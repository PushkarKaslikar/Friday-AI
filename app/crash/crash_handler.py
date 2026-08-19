"""Crash Handler intercepting unhandled exceptions and generating diagnostic crash reports."""

import datetime
import faulthandler
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from app.constants.application import APP_NAME, APP_VERSION
from app.constants.paths import PROJECT_ROOT
from app.logging import logger
from app.utilities.file_utils import write_json_file
from app.utilities.path_utils import ensure_directory_exists

CRASH_REPORT_DIR = PROJECT_ROOT / "crash_reports"


class CrashHandler:
    """Centralized crash handler registering faulthandler and generating structured crash logs."""

    def __init__(self, report_dir: str | Path | None = None) -> None:
        self.report_dir = ensure_directory_exists(report_dir or CRASH_REPORT_DIR)
        self._installed = False

    def install(self) -> None:
        """Enable C-level faulthandler and set sys.excepthook to trap crashes."""
        if self._installed:
            return

        # Enable C-level signal stack trace dump
        fault_file = self.report_dir / "faulthandler.log"
        try:
            fault_stream = open(fault_file, "a", encoding="utf-8")  # noqa: SIM115
            faulthandler.enable(file=fault_stream)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"CrashHandler: Could not attach faulthandler stream: {exc}")

        # Install Python unhandled exception hook
        sys.excepthook = self._handle_unhandled_exception
        self._installed = True
        logger.info("CrashHandler installed and listening for process crashes.")

    def _handle_unhandled_exception(
        self, exc_type: type, exc_value: BaseException, exc_tb: Any
    ) -> None:
        """Intercept unhandled exceptions, log via Loguru, and generate crash report file."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        safe_msg = str(exc_value).replace("{", "{{").replace("}", "}}")
        logger.critical(
            f"CrashHandler: Trapped unhandled crash! {exc_type.__name__}: {safe_msg}"
        )

        try:
            report_file = self.generate_crash_report(exc_type, exc_value, exc_tb)
            print(
                f"[FATAL CRASH] Crash report generated at: {report_file}",
                file=sys.stderr,
            )
        except Exception as report_exc:  # noqa: BLE001
            print(
                f"[FATAL CRASH] Failed to generate crash report: {report_exc}",
                file=sys.stderr,
            )

    def generate_crash_report(
        self,
        exc_type: type,
        exc_value: BaseException,
        exc_tb: Any,
        extra_data: dict[str, Any] | None = None,
    ) -> Path:
        """Generate a structured JSON crash report file.

        Returns:
            Path: Path to created crash report JSON file.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005
        report_file = self.report_dir / f"crash_{timestamp}.json"

        stack_frames = traceback.format_exception(exc_type, exc_value, exc_tb)

        report_data = {
            "app_name": APP_NAME,
            "version": APP_VERSION,
            "timestamp": str(datetime.datetime.now()),  # noqa: DTZ005
            "python_version": sys.version,
            "os_platform": sys.platform,
            "pid": os.getpid(),
            "exception": {
                "type": exc_type.__name__,
                "message": str(exc_value),
                "traceback": stack_frames,
            },
            "extra_context": extra_data or {},
        }

        write_json_file(report_file, report_data)
        return report_file
