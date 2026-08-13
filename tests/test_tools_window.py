"""Unit tests for Window Management tools."""

from app.tools.builtin.window_tools import (
    ActiveWindowTool,
    CloseWindowTool,
    MaximizeWindowTool,
    MinimizeWindowTool,
    RestoreWindowTool,
    WindowListTool,
)


def test_window_list_tool():
    tool = WindowListTool()
    res = tool.execute({})
    assert res.success is True
    assert "windows" in res.result_data


def test_active_window_tool():
    tool = ActiveWindowTool()
    res = tool.execute({})
    assert res.success is True
    assert "title" in res.result_data


def test_window_state_tools():
    min_tool = MinimizeWindowTool()
    res_min = min_tool.execute({"hwnd": 1001})
    assert res_min.success is True

    max_tool = MaximizeWindowTool()
    res_max = max_tool.execute({"hwnd": 1001})
    assert res_max.success is True

    rest_tool = RestoreWindowTool()
    res_rest = rest_tool.execute({"hwnd": 1001})
    assert res_rest.success is True

    close_tool = CloseWindowTool()
    res_close = close_tool.execute({"hwnd": 1001})
    assert res_close.success is True
