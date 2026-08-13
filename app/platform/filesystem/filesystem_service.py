"""Filesystem service encapsulating streaming file operations, Recycle Bin deletion, search, hashing, and batch processing."""

import ctypes
import hashlib
import os
import shutil
import time
from pathlib import Path
from typing import Any

from app.logging import logger
from app.platform.filesystem.models import (
    DirectoryEntry,
    FileHashResult,
    WorkspaceSummary,
)
from app.platform.filesystem.path_security import PathSecurityManager
from app.tools.execution.cancellation import CancellationToken
from app.tools.models.errors import ToolErrorCode, ToolExecutionError


def _send_to_recycle_bin(path_str: str) -> bool:
    """Send target file or directory to Windows Recycle Bin via SHFileOperationW."""
    try:
        from ctypes import wintypes

        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", wintypes.UINT),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", wintypes.WORD),
                ("fAnyOperationsAborted", wintypes.BOOL),
                ("hNameMappings", wintypes.LPVOID),
                ("lpszProgressTitle", wintypes.LPCWSTR),
            ]

        FO_DELETE = 0x0003
        FOF_ALLOWUNDO = 0x0040
        FOF_NOCONFIRMATION = 0x0010
        FOF_SILENT = 0x0004

        # pFrom requires double null-terminated string
        double_null_path = path_str + "\0\0"
        fileop = SHFILEOPSTRUCTW()
        fileop.hwnd = None
        fileop.wFunc = FO_DELETE
        fileop.pFrom = double_null_path
        fileop.pTo = None
        fileop.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
        fileop.fAnyOperationsAborted = False

        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(fileop))
        return res == 0
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Recycle Bin SHFileOperationW failed for '{path_str}': {exc}")
        return False


class FilesystemService:
    """Core filesystem engine providing high-level operations for files, directories, hashing, search, and workspace metrics."""

    def __init__(self, security_manager: PathSecurityManager | None = None) -> None:
        self.security = security_manager or PathSecurityManager()

    def create_file(
        self, path_str: str, content: str = "", overwrite: bool = False
    ) -> dict[str, Any]:
        """Create a new file with optional UTF-8 string content."""
        target = self.security.validate_path(path_str, check_protected=True)

        if target.exists() and not overwrite:
            raise ToolExecutionError(
                error_code=ToolErrorCode.PERMISSION_DENIED,
                message=f"File '{target}' already exists and overwrite=False.",
            )

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            stat = target.stat()
            return {
                "path": str(target),
                "size_bytes": stat.st_size,
                "overwritten": target.exists() and overwrite,
                "created": True,
            }
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to create file '{target}': {exc}",
            ) from exc

    def create_folder(self, path_str: str) -> dict[str, Any]:
        """Create a single or nested directory folder structure."""
        target = self.security.validate_path(path_str, check_protected=True)

        try:
            target.mkdir(parents=True, exist_ok=True)
            return {"path": str(target), "created": True}
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to create directory '{target}': {exc}",
            ) from exc

    def copy_file(
        self, src_str: str, dest_str: str, overwrite: bool = False
    ) -> dict[str, Any]:
        """Copy a single file from src to dest."""
        src = self.security.validate_path(src_str, must_exist=True, must_be_file=True)
        dest = self.security.normalize(dest_str)

        if dest.is_dir():
            dest = dest / src.name

        self.security.validate_destination(
            src, dest, allow_overwrite=overwrite, check_protected=True
        )

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return {
                "source": str(src),
                "destination": str(dest),
                "copied": True,
                "size_bytes": dest.stat().st_size,
            }
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to copy file from '{src}' to '{dest}': {exc}",
            ) from exc

    def copy_folder(
        self,
        src_str: str,
        dest_str: str,
        overwrite: bool = False,
        cancellation_token: CancellationToken | None = None,
    ) -> dict[str, Any]:
        """Copy an entire directory folder tree with recursive self-copy prevention."""
        src = self.security.validate_path(src_str, must_exist=True, must_be_dir=True)
        dest = self.security.normalize(dest_str)

        self.security.validate_destination(
            src, dest, allow_overwrite=overwrite, check_protected=True
        )

        try:
            if cancellation_token and cancellation_token.is_cancelled:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.CANCELLED,
                    message="Copy folder operation cancelled.",
                )

            shutil.copytree(src, dest, dirs_exist_ok=overwrite)
            return {"source": str(src), "destination": str(dest), "copied": True}
        except Exception as exc:
            if isinstance(exc, ToolExecutionError):
                raise
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to copy folder from '{src}' to '{dest}': {exc}",
            ) from exc

    def move_item(
        self, src_str: str, dest_str: str, overwrite: bool = False
    ) -> dict[str, Any]:
        """Move a file or directory safely across volumes."""
        src = self.security.validate_path(src_str, must_exist=True)
        dest = self.security.normalize(dest_str)

        if dest.is_dir() and src.is_file():
            dest = dest / src.name

        self.security.validate_destination(
            src, dest, allow_overwrite=overwrite, check_protected=True
        )

        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            return {"source": str(src), "destination": str(dest), "moved": True}
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to move '{src}' to '{dest}': {exc}",
            ) from exc

    def rename_item(self, path_str: str, new_name: str) -> dict[str, Any]:
        """Rename a file or folder in-place without path traversal."""
        clean_new_name = self.security.validate_filename(new_name)
        target = self.security.validate_path(
            path_str, must_exist=True, check_protected=True
        )
        new_path = target.parent / clean_new_name

        if new_path.exists():
            raise ToolExecutionError(
                error_code=ToolErrorCode.PERMISSION_DENIED,
                message=f"Cannot rename '{target.name}': Target name '{clean_new_name}' already exists in directory.",
            )

        try:
            target.rename(new_path)
            return {"old_path": str(target), "new_path": str(new_path), "renamed": True}
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to rename '{target}' to '{clean_new_name}': {exc}",
            ) from exc

    def delete_item(
        self, path_str: str, use_recycle_bin: bool = True
    ) -> dict[str, Any]:
        """Delete a file or directory safely (defaults to Windows Recycle Bin)."""
        target = self.security.validate_path(
            path_str, must_exist=True, check_protected=True
        )
        is_dir = target.is_dir()

        recycled = False
        if use_recycle_bin:
            recycled = _send_to_recycle_bin(str(target))

        if not recycled:
            try:
                if is_dir:
                    shutil.rmtree(target)
                else:
                    target.unlink()
            except Exception as exc:
                raise ToolExecutionError(
                    error_code=ToolErrorCode.EXECUTION_FAILED,
                    message=f"Failed to delete '{target}': {exc}",
                ) from exc

        return {
            "path": str(target),
            "deleted": True,
            "recycle_bin_used": recycled,
            "is_directory": is_dir,
        }

    def list_directory(
        self, path_str: str, recursive: bool = False, include_hidden: bool = False
    ) -> list[DirectoryEntry]:
        """List entries inside a target directory folder."""
        target = self.security.validate_path(
            path_str, must_exist=True, must_be_dir=True
        )
        entries: list[DirectoryEntry] = []

        def _scan(directory: Path, current_depth: int):
            if current_depth > 3 and recursive:
                return
            try:
                for item in directory.iterdir():
                    is_hidden = (
                        item.name.startswith(".")
                        or bool(item.stat().st_file_attributes & 2)
                        if os.name == "nt"
                        else item.name.startswith(".")
                    )
                    if is_hidden and not include_hidden:
                        continue

                    stat = item.stat()
                    fmt_time = lambda ts: time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(ts)
                    )
                    entries.append(
                        DirectoryEntry(
                            name=item.name,
                            path=str(item),
                            is_directory=item.is_dir(),
                            size_bytes=stat.st_size if not item.is_dir() else 0,
                            created_time=fmt_time(stat.st_ctime),
                            modified_time=fmt_time(stat.st_mtime),
                            extension=item.suffix,
                            is_hidden=is_hidden,
                        )
                    )
                    if recursive and item.is_dir():
                        _scan(item, current_depth + 1)
            except PermissionError:
                pass

        _scan(target, 1)
        return entries

    def search(
        self,
        root_path_str: str,
        pattern: str = "*",
        extension: str | None = None,
        max_results: int = 100,
        max_depth: int = 5,
        cancellation_token: CancellationToken | None = None,
    ) -> dict[str, Any]:
        """Perform recursive directory file search with limits and cancellation monitoring."""
        root = self.security.validate_path(
            root_path_str, must_exist=True, must_be_dir=True
        )
        results: list[dict[str, Any]] = []
        truncated = False

        ext_clean = extension.lower() if extension else None
        if ext_clean and not ext_clean.startswith("."):
            ext_clean = f".{ext_clean}"

        def _search_dir(current_dir: Path, depth: int):
            nonlocal truncated
            if depth > max_depth or len(results) >= max_results:
                if len(results) >= max_results:
                    truncated = True
                return

            if cancellation_token and cancellation_token.is_cancelled:
                return

            try:
                for item in current_dir.iterdir():
                    if len(results) >= max_results:
                        truncated = True
                        break

                    if item.is_file():
                        if ext_clean and item.suffix.lower() != ext_clean:
                            continue
                        if pattern != "*" and pattern.lower() not in item.name.lower():
                            continue

                        stat = item.stat()
                        results.append(
                            {
                                "name": item.name,
                                "path": str(item),
                                "size_bytes": stat.st_size,
                                "extension": item.suffix,
                            }
                        )
                    elif item.is_dir():
                        _search_dir(item, depth + 1)
            except PermissionError:
                pass

        _search_dir(root, 1)
        return {
            "root": str(root),
            "count": len(results),
            "truncated": truncated,
            "results": results,
        }

    def hash_file(self, path_str: str, algorithm: str = "sha256") -> FileHashResult:
        """Calculate cryptographic hash of a file using chunked streaming."""
        target = self.security.validate_path(
            path_str, must_exist=True, must_be_file=True
        )
        algo_name = algorithm.lower().strip()

        if algo_name not in ("sha256", "md5", "sha1"):
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Unsupported hash algorithm '{algorithm}'. Supported: sha256, md5, sha1.",
            )

        hasher = getattr(hashlib, algo_name)()
        try:
            with open(target, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            return FileHashResult(
                path=str(target),
                algorithm=algo_name.upper(),
                hash_value=hasher.hexdigest(),
                size_bytes=target.stat().st_size,
            )
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to hash file '{target}': {exc}",
            ) from exc

    def workspace_info(self, path_str: str) -> WorkspaceSummary:
        """Query aggregate high-level metrics for a directory workspace."""
        root = self.security.validate_path(path_str, must_exist=True, must_be_dir=True)
        file_count = 0
        folder_count = 0
        total_bytes = 0
        ext_counts: dict[str, int] = {}

        try:
            for item in root.rglob("*"):
                if item.is_file():
                    file_count += 1
                    sz = item.stat().st_size
                    total_bytes += sz
                    ext = item.suffix.lower() or "no_extension"
                    ext_counts[ext] = ext_counts.get(ext, 0) + 1
                elif item.is_dir():
                    folder_count += 1
        except PermissionError:
            pass

        return WorkspaceSummary(
            path=str(root),
            file_count=file_count,
            folder_count=folder_count,
            total_size_bytes=total_bytes,
            total_size_mb=round(total_bytes / (1024 * 1024), 2),
            extension_counts=ext_counts,
        )
