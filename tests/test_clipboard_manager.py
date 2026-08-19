"""Unit tests for ClipboardManager read/write, format inspection, secret masking, and user clipboard restoration."""

import sys

import pytest

from app.automation.desktop.clipboard_manager import ClipboardManager


@pytest.mark.skipif(
    sys.platform != "win32", reason="Clipboard tests require Win32 platform"
)
def test_clipboard_read_write_and_secret_masking():
    cb = ClipboardManager()
    backup = cb.backup_clipboard()

    try:
        # 1. Normal text write and read
        test_str = "Friday Unit Test String"
        cb.set_text(test_str)
        res = cb.get_text(mask_secrets=True)

        assert res.status == "COMPLETED"
        assert res.text == test_str
        assert res.is_masked is False

        # 2. Secret text write and read (secret masking)
        secret_str = "password=SuperSecretPassword123"
        cb.set_text(secret_str)
        sec_res = cb.get_text(mask_secrets=True)

        assert sec_res.status == "COMPLETED"
        assert sec_res.is_masked is True
        assert "SuperSecretPassword123" not in sec_res.text
        assert "********" in sec_res.text
    finally:
        cb.restore_clipboard(backup)
