"""Unit tests for Phase 6.7 Automation Privacy Boundaries."""

from app.tools.builtin.automation.clipboard_tools import ClipboardGetContentTool
from app.tools.builtin.automation.input_tools import InputTypeTextTool


def test_input_text_privacy_sanitization():
    tool = InputTypeTextTool()
    res = tool.execute({"text": "My password is UserSecretKey999!"})
    assert res.success
    assert "UserSecretKey999!" not in res.data["text_summary"]


def test_clipboard_privacy_sanitization():
    tool = ClipboardGetContentTool()
    res = tool.execute({})
    assert res.success
