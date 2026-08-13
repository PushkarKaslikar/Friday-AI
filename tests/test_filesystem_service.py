"""Unit tests for FilesystemService."""

from app.platform.filesystem.filesystem_service import FilesystemService


def test_create_file_and_folder(tmp_path):
    service = FilesystemService()

    folder_res = service.create_folder(str(tmp_path / "test_dir"))
    assert folder_res["created"] is True

    file_res = service.create_file(
        str(tmp_path / "test_dir" / "file.txt"), content="Friday AI content"
    )
    assert file_res["created"] is True
    assert file_res["size_bytes"] > 0


def test_copy_file_and_folder(tmp_path):
    service = FilesystemService()
    src_file = tmp_path / "src.txt"
    src_file.write_text("Hello Copy")

    dest_file = tmp_path / "dest.txt"
    copy_res = service.copy_file(str(src_file), str(dest_file))
    assert copy_res["copied"] is True
    assert dest_file.read_text() == "Hello Copy"

    # Copy folder
    src_folder = tmp_path / "folder1"
    src_folder.mkdir()
    (src_folder / "item.txt").write_text("item")

    dest_folder = tmp_path / "folder2"
    copy_f_res = service.copy_folder(str(src_folder), str(dest_folder))
    assert copy_f_res["copied"] is True
    assert (dest_folder / "item.txt").exists()


def test_move_and_rename_item(tmp_path):
    service = FilesystemService()
    file1 = tmp_path / "file1.txt"
    file1.write_text("Move Content")

    file2 = tmp_path / "file2.txt"
    move_res = service.move_item(str(file1), str(file2))
    assert move_res["moved"] is True
    assert not file1.exists()
    assert file2.exists()

    rename_res = service.rename_item(str(file2), "file3.txt")
    assert rename_res["renamed"] is True
    assert (tmp_path / "file3.txt").exists()


def test_hash_and_search_files(tmp_path):
    service = FilesystemService()
    (tmp_path / "sample1.pdf").write_text("PDF Content 1")
    (tmp_path / "sample2.pdf").write_text("PDF Content 2")
    (tmp_path / "other.txt").write_text("Text Content")

    hash_res = service.hash_file(str(tmp_path / "sample1.pdf"))
    assert hash_res.algorithm == "SHA256"
    assert len(hash_res.hash_value) == 64

    search_res = service.search(str(tmp_path), pattern="sample", extension=".pdf")
    assert search_res["count"] == 2


def test_workspace_info(tmp_path):
    service = FilesystemService()
    (tmp_path / "file1.txt").write_text("Content 1")
    (tmp_path / "file2.py").write_text("Content 2")
    (tmp_path / "sub").mkdir()

    summary = service.workspace_info(str(tmp_path))
    assert summary.file_count == 2
    assert summary.folder_count == 1
    assert summary.extension_counts[".txt"] == 1
    assert summary.extension_counts[".py"] == 1
