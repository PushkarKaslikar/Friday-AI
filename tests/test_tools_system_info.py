"""Unit tests for System Information tools."""

from app.tools.builtin.system_info_tools import (
    CpuInfoTool,
    CurrentUserTool,
    DiskInfoTool,
    MemoryInfoTool,
    UptimeTool,
    WindowsInfoTool,
)


def test_cpu_info_tool():
    tool = CpuInfoTool()
    res = tool.execute({"include_per_cpu": True})
    assert res.success is True
    assert "processor" in res.result_data
    assert res.result_data["logical_cores"] >= 1
    assert "per_cpu_percent" in res.result_data


def test_memory_info_tool():
    tool = MemoryInfoTool()
    res = tool.execute({})
    assert res.success is True
    assert res.result_data["total_gb"] > 0
    assert 0 <= res.result_data["usage_percent"] <= 100


def test_disk_info_tool():
    tool = DiskInfoTool()
    res = tool.execute({})
    assert res.success is True
    assert "drives" in res.result_data
    assert len(res.result_data["drives"]) >= 1


def test_windows_info_tool():
    tool = WindowsInfoTool()
    res = tool.execute({})
    assert res.success is True
    assert res.result_data["os_name"] == "Windows"


def test_uptime_tool():
    tool = UptimeTool()
    res = tool.execute({})
    assert res.success is True
    assert res.result_data["uptime_seconds"] > 0


def test_current_user_tool():
    tool = CurrentUserTool()
    res = tool.execute({})
    assert res.success is True
    assert res.result_data["username"] != ""
