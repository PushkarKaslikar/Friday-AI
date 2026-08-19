"""Safe Win32 clipboard format inspection, reading, writing, and secret masking service."""

import sys
import time

from app.automation.desktop.errors import (
    ClipboardSizeLimitError,
    ClipboardUnavailableError,
)
from app.automation.desktop.models import ClipboardFormat, ClipboardResult
from app.logging import logger
from app.tools.execution.result_normalizer import SensitiveDataSanitizer

try:
    import win32clipboard
    import win32con

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class ClipboardManager:
    """Safe Windows clipboard format inspector, reader, writer, and secret masking service."""

    def __init__(self, max_text_chars: int = 100000) -> None:
        self.max_text_chars = max_text_chars

    def is_available(self) -> bool:
        """Check if Win32 clipboard access is available."""
        return sys.platform == "win32" and PYWIN32_AVAILABLE

    def inspect_format(self) -> ClipboardFormat:
        """Inspect current Windows clipboard content format."""
        if not self.is_available():
            return ClipboardFormat.UNSUPPORTED

        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                    return ClipboardFormat.UNICODE_TEXT
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                    return ClipboardFormat.TEXT
                elif win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    return ClipboardFormat.FILE_LIST
                elif win32clipboard.CountClipboardFormats() == 0:
                    return ClipboardFormat.EMPTY
                else:
                    return ClipboardFormat.UNSUPPORTED
            finally:
                win32clipboard.CloseClipboard()
        except Exception as exc:
            logger.debug(f"Failed to inspect clipboard format: {exc}")
            return ClipboardFormat.UNSUPPORTED

    def get_text(self, mask_secrets: bool = True) -> ClipboardResult:
        """Read safe text string from clipboard. Applies secret masking if enabled."""
        if not self.is_available():
            raise ClipboardUnavailableError("Win32 clipboard access unavailable.")

        t0 = time.perf_counter()
        try:
            win32clipboard.OpenClipboard()
            try:
                if not (
                    win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT)
                    or win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT)
                ):
                    return ClipboardResult(
                        status="EMPTY",
                        format=ClipboardFormat.EMPTY,
                        text=None,
                        size_bytes=0,
                    )

                raw_data = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                text = str(raw_data) if raw_data is not None else ""
            finally:
                win32clipboard.CloseClipboard()

            if len(text) > self.max_text_chars:
                raise ClipboardSizeLimitError(
                    f"Clipboard text length ({len(text)}) exceeds maximum cap ({self.max_text_chars})."
                )

            is_masked = False
            clean_text = text
            if mask_secrets and text:
                clean_text = SensitiveDataSanitizer.sanitize_text(text)
                is_masked = clean_text != text

            return ClipboardResult(
                status="COMPLETED",
                format=ClipboardFormat.UNICODE_TEXT,
                text=clean_text,
                is_masked=is_masked,
                size_bytes=len(text.encode("utf-8")),
            )
        except (ClipboardSizeLimitError, ClipboardUnavailableError):
            raise
        except Exception as exc:
            logger.error(f"Failed to read clipboard text: {exc}")
            raise ClipboardUnavailableError(
                "Could not read clipboard content.", cause=exc
            )

    def set_text(self, text: str) -> ClipboardResult:
        """Write text string safely to Windows clipboard."""
        if not self.is_available():
            raise ClipboardUnavailableError("Win32 clipboard access unavailable.")

        if text and len(text) > self.max_text_chars:
            raise ClipboardSizeLimitError(
                f"Text string length ({len(text)}) exceeds maximum cap ({self.max_text_chars})."
            )

        t0 = time.perf_counter()
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                if text:
                    win32clipboard.SetClipboardText(str(text), win32con.CF_UNICODETEXT)
            finally:
                win32clipboard.CloseClipboard()

            return ClipboardResult(
                status="COMPLETED",
                format=ClipboardFormat.UNICODE_TEXT,
                text=text,
                size_bytes=len((text or "").encode("utf-8")),
            )
        except (ClipboardSizeLimitError, ClipboardUnavailableError):
            raise
        except Exception as exc:
            logger.error(f"Failed to write clipboard text: {exc}")
            raise ClipboardUnavailableError("Could not write to clipboard.", cause=exc)

    def get_file_list(self) -> list[str]:
        """Inspect file drop list from clipboard if CF_HDROP format is present."""
        if not self.is_available():
            return []

        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    # Win32 GetClipboardData for CF_HDROP returns tuple of file paths
                    data = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                    if isinstance(data, (tuple, list)):
                        return [str(p) for p in data]
            finally:
                win32clipboard.CloseClipboard()
        except Exception as exc:
            logger.debug(f"Failed to read clipboard file list: {exc}")
        return []

    def clear(self) -> None:
        """Clear Windows clipboard content safely."""
        if not self.is_available():
            return

        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
            finally:
                win32clipboard.CloseClipboard()
        except Exception as exc:
            logger.debug(f"Failed to clear clipboard: {exc}")

    def backup_clipboard(self) -> str | None:
        """Helper to read current text for developer test restoration."""
        try:
            res = self.get_text(mask_secrets=False)
            return res.text
        except Exception:
            return None

    def restore_clipboard(self, backup_text: str | None) -> None:
        """Helper to restore original developer text after test runs."""
        try:
            if backup_text is not None:
                self.set_text(backup_text)
            else:
                self.clear()
        except Exception as exc:
            logger.debug(f"Failed to restore clipboard backup: {exc}")
