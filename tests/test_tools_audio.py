"""Unit tests for Audio and Volume tools."""

from app.tools.builtin.audio_tools import (
    GetVolumeTool,
    MuteAudioTool,
    SetVolumeTool,
    UnmuteAudioTool,
)
from app.tools.models.errors import ToolErrorCode


def test_get_volume_tool():
    tool = GetVolumeTool()
    res = tool.execute({})
    assert res.success is True
    assert "volume" in res.result_data
    assert "is_muted" in res.result_data


def test_set_volume_tool():
    tool = SetVolumeTool()
    res = tool.execute({"volume": 75})
    assert res.success is True
    assert res.result_data["volume"] == 75


def test_set_volume_tool_invalid():
    tool = SetVolumeTool()
    res = tool.execute({"volume": 150})
    assert res.success is False
    assert res.error_code == ToolErrorCode.INVALID_INPUT


def test_mute_unmute_audio_tools():
    mute_tool = MuteAudioTool()
    res_mute = mute_tool.execute({})
    assert res_mute.success is True
    assert res_mute.result_data["is_muted"] is True

    unmute_tool = UnmuteAudioTool()
    res_unmute = unmute_tool.execute({})
    assert res_unmute.success is True
    assert res_unmute.result_data["is_muted"] is False
