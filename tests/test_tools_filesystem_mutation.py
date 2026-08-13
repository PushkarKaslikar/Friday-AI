"""Unit tests for Phase 2.4 filesystem tools executing through BaseTool."""

from app.tools.builtin.file_tools import (
    CalculateSizeTool,
    CopyFileTool,
    CreateFileTool,
    ListDirectoryTool,
)
from app.tools.builtin.filesystem_mutation_tools import (
    BatchOperationTool,
    CompareFilesTool,
    HashFileTool,
    MoveFileTool,
    RenameFileTool,
    SearchFilesTool,
)


def test_create_and_copy_file_tools(tmp_path):
    create_tool = CreateFileTool()
    file_path = tmp_path / "created.txt"
    res_create = create_tool.execute(
        {"path": str(file_path), "content": "Hello BaseTool"}
    )
    assert res_create.success is True
    assert file_path.exists()

    copy_tool = CopyFileTool()
    dest_path = tmp_path / "copied.txt"
    res_copy = copy_tool.execute(
        {"source": str(file_path), "destination": str(dest_path)}
    )
    assert res_copy.success is True
    assert dest_path.exists()


def test_list_directory_and_calculate_size_tools(tmp_path):
    (tmp_path / "file1.txt").write_text("Hello")
    (tmp_path / "file2.txt").write_text("World")

    list_tool = ListDirectoryTool()
    res_list = list_tool.execute({"path": str(tmp_path)})
    assert res_list.success is True
    assert res_list.result_data["count"] == 2

    size_tool = CalculateSizeTool()
    res_size = size_tool.execute({"path": str(tmp_path)})
    assert res_size.success is True
    assert res_size.result_data["file_count"] == 2


def test_move_and_rename_tools(tmp_path):
    f1 = tmp_path / "f1.txt"
    f1.write_text("content")

    move_tool = MoveFileTool()
    f2 = tmp_path / "f2.txt"
    res_move = move_tool.execute({"source": str(f1), "destination": str(f2)})
    assert res_move.success is True
    assert f2.exists()

    rename_tool = RenameFileTool()
    res_rename = rename_tool.execute({"path": str(f2), "new_name": "f3.txt"})
    assert res_rename.success is True
    assert (tmp_path / "f3.txt").exists()


def test_search_and_hash_tools(tmp_path):
    f = tmp_path / "document.pdf"
    f.write_text("PDF content data")

    search_tool = SearchFilesTool()
    res_search = search_tool.execute(
        {"root_path": str(tmp_path), "pattern": "document", "extension": ".pdf"}
    )
    assert res_search.success is True
    assert res_search.result_data["count"] == 1

    hash_tool = HashFileTool()
    res_hash = hash_tool.execute({"path": str(f)})
    assert res_hash.success is True
    assert "hash_value" in res_hash.result_data


def test_compare_files_tool(tmp_path):
    f1 = tmp_path / "a.txt"
    f2 = tmp_path / "b.txt"
    f1.write_text("Identical")
    f2.write_text("Identical")

    compare_tool = CompareFilesTool()
    res = compare_tool.execute({"file1": str(f1), "file2": str(f2)})
    assert res.success is True
    assert res.result_data["identical"] is True


def test_batch_operation_tool(tmp_path):
    f1 = tmp_path / "batch1.txt"
    f2 = tmp_path / "batch2.txt"
    f1.write_text("1")
    f2.write_text("2")

    target_dir = tmp_path / "target"
    target_dir.mkdir()

    batch_tool = BatchOperationTool()
    res = batch_tool.execute(
        {
            "operation_type": "copy",
            "sources": [str(f1), str(f2)],
            "destination_folder": str(target_dir),
        }
    )
    assert res.success is True
    assert res.result_data["successful_items"] == 2
    assert (target_dir / "batch1.txt").exists()
    assert (target_dir / "batch2.txt").exists()
