"""Unit tests for File and Folder tools."""

from app.tools.builtin.file_tools import (
    FileExistsTool,
    FileInfoTool,
    FolderExistsTool,
    FolderInfoTool,
    OpenFileTool,
)
from app.tools.models.errors import ToolErrorCode


def test_file_exists_tool(tmp_path):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Hello Friday AI")

    tool = FileExistsTool()
    res = tool.execute({"path": str(test_file)})
    assert res.success is True
    assert res.result_data["exists"] is True

    res_missing = tool.execute({"path": str(tmp_path / "missing.txt")})
    assert res_missing.success is True
    assert res_missing.result_data["exists"] is False


def test_folder_exists_tool(tmp_path):
    tool = FolderExistsTool()
    res = tool.execute({"path": str(tmp_path)})
    assert res.success is True
    assert res.result_data["exists"] is True


def test_file_info_tool(tmp_path):
    test_file = tmp_path / "info.txt"
    test_file.write_text("Testing file metadata")

    tool = FileInfoTool()
    res = tool.execute({"path": str(test_file)})
    assert res.success is True
    assert res.result_data["filename"] == "info.txt"
    assert res.result_data["size_bytes"] > 0


def test_folder_info_tool(tmp_path):
    (tmp_path / "subfile.txt").write_text("content")
    (tmp_path / "subdir").mkdir()

    tool = FolderInfoTool()
    res = tool.execute({"path": str(tmp_path)})
    assert res.success is True
    assert res.result_data["file_count"] == 1
    assert res.result_data["subdirectory_count"] == 1


def test_open_file_invalid_path():
    tool = OpenFileTool()
    res = tool.execute({"path": "C:\\nonexistent_file_path_12345.xyz"})
    assert res.success is False
    assert res.error_code == ToolErrorCode.INVALID_INPUT
