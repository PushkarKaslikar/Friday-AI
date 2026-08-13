"""Unit tests for Application management tools."""

from app.tools.builtin.application_tools import (
    ApplicationStatusTool,
    CloseApplicationTool,
    OpenApplicationTool,
)


def test_open_application_tool():
    tool = OpenApplicationTool()
    res = tool.execute({"application": "calc"})
    assert res.success is True
    assert res.result_data["launched"] is True


def test_application_status_tool():
    tool = ApplicationStatusTool()
    res = tool.execute({"application_name": "explorer"})
    assert res.success is True
    assert "is_running" in res.result_data


def test_close_application_nonexistent():
    tool = CloseApplicationTool()
    res = tool.execute({"application_name": "nonexistent_fake_app_xyz"})
    assert res.success is True
    assert res.result_data["closed"] is False
