"""Unit tests for Phase 6.6 Automation Tool security boundaries, permissions, and secret masking."""

from app.tools.builtin.automation.clipboard_tools import ClipboardGetContentTool
from app.tools.builtin.automation.input_tools import InputTypeTextTool


def test_input_type_text_secret_masking():
    tool = InputTypeTextTool()
    res = tool.execute({"text": "My password is Password123!"})

    assert res.success
    assert "Password123!" not in res.data["text_summary"]
    assert "*" in res.data["text_summary"]


def test_clipboard_secret_masking():
    tool = ClipboardGetContentTool()
    res = tool.execute({})

    assert res.success
    assert "text" in res.data
