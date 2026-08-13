"""Unit tests for Clipboard tools."""

from app.tools.builtin.clipboard_tools import ReadClipboardTool, WriteClipboardTool


def test_clipboard_write_and_read():
    write_tool = WriteClipboardTool()
    res_write = write_tool.execute({"text": "Friday AI Clipboard Test"})
    assert res_write.success is True

    read_tool = ReadClipboardTool()
    res_read = read_tool.execute({})
    assert res_read.success is True
    assert res_read.result_data["text"] == "Friday AI Clipboard Test"
