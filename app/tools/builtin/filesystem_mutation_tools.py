"""Filesystem mutation, search, hashing, workspace metrics, and batch operation tools."""

import os
from typing import Any

from pydantic import BaseModel, Field

from app.logging import logger
from app.platform.filesystem.filesystem_service import FilesystemService
from app.platform.filesystem.models import BatchOperationFailure, BatchResult
from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory
from app.tools.models.errors import ToolErrorCode, ToolExecutionError


# 1. Move File Tool
class MoveFileInput(BaseModel):
    """Input parameters for MoveFileTool."""

    source: str = Field(description="Source file path")
    destination: str = Field(description="Target destination file or directory path")
    overwrite: bool = Field(
        default=False, description="Whether to allow overwriting destination"
    )


class MoveFileTool(BaseTool):
    """Tool moving a file from source to destination."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.move_file",
            name="move_file",
            display_name="Move File",
            description="Moves a single file from source to destination. High risk operation.",
            category=ToolCategory.FILES,
            tags=["file", "move", "filesystem"],
            input_schema=MoveFileInput,
            risk_level=ToolRiskLevel.HIGH,
            permissions=[ToolPermission.FILESYSTEM_MOVE],
            confirmation_required=True,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: MoveFileInput = validated_input  # type: ignore
        return self.service.move_item(
            src_str=inp.source, dest_str=inp.destination, overwrite=inp.overwrite
        )


# 2. Move Folder Tool
class MoveFolderInput(BaseModel):
    """Input parameters for MoveFolderTool."""

    source: str = Field(description="Source directory folder path")
    destination: str = Field(description="Target destination directory path")
    overwrite: bool = Field(
        default=False, description="Whether to allow overwriting destination"
    )


class MoveFolderTool(BaseTool):
    """Tool moving an entire directory folder tree."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.move_folder",
            name="move_folder",
            display_name="Move Folder",
            description="Moves an entire directory folder tree. High risk operation.",
            category=ToolCategory.FILES,
            tags=["folder", "move", "filesystem"],
            input_schema=MoveFolderInput,
            risk_level=ToolRiskLevel.HIGH,
            permissions=[ToolPermission.FILESYSTEM_MOVE],
            confirmation_required=True,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: MoveFolderInput = validated_input  # type: ignore
        return self.service.move_item(
            src_str=inp.source, dest_str=inp.destination, overwrite=inp.overwrite
        )


# 3. Rename File Tool
class RenameFileInput(BaseModel):
    """Input parameters for RenameFileTool."""

    path: str = Field(description="Target file path to rename")
    new_name: str = Field(
        description="New target filename string (basename only, no path traversal)"
    )


class RenameFileTool(BaseTool):
    """Tool renaming a file in-place without path traversal."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.rename_file",
            name="rename_file",
            display_name="Rename File",
            description="Renames a target file in-place.",
            category=ToolCategory.FILES,
            tags=["file", "rename", "filesystem"],
            input_schema=RenameFileInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.FILESYSTEM_RENAME],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: RenameFileInput = validated_input  # type: ignore
        return self.service.rename_item(path_str=inp.path, new_name=inp.new_name)


# 4. Rename Folder Tool
class RenameFolderInput(BaseModel):
    """Input parameters for RenameFolderTool."""

    path: str = Field(description="Target directory folder path to rename")
    new_name: str = Field(description="New target folder name string (basename only)")


class RenameFolderTool(BaseTool):
    """Tool renaming a directory folder in-place."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.rename_folder",
            name="rename_folder",
            display_name="Rename Folder",
            description="Renames a target directory folder in-place.",
            category=ToolCategory.FILES,
            tags=["folder", "rename", "filesystem"],
            input_schema=RenameFolderInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.FILESYSTEM_RENAME],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: RenameFolderInput = validated_input  # type: ignore
        return self.service.rename_item(path_str=inp.path, new_name=inp.new_name)


# 5. Delete File Tool
class DeleteFileInput(BaseModel):
    """Input parameters for DeleteFileTool."""

    path: str = Field(description="Target file path to delete")
    use_recycle_bin: bool = Field(
        default=True, description="Whether to send to Windows Recycle Bin"
    )


class DeleteFileTool(BaseTool):
    """Tool safely deleting a target file (defaults to Recycle Bin)."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.delete_file",
            name="delete_file",
            display_name="Delete File",
            description="Safely deletes a file (defaults to Windows Recycle Bin). High risk operation.",
            category=ToolCategory.FILES,
            tags=["file", "delete", "recycle", "filesystem"],
            input_schema=DeleteFileInput,
            risk_level=ToolRiskLevel.HIGH,
            permissions=[ToolPermission.FILESYSTEM_DELETE],
            confirmation_required=True,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: DeleteFileInput = validated_input  # type: ignore
        return self.service.delete_item(
            path_str=inp.path, use_recycle_bin=inp.use_recycle_bin
        )


# 6. Delete Folder Tool
class DeleteFolderInput(BaseModel):
    """Input parameters for DeleteFolderTool."""

    path: str = Field(description="Target directory folder path to delete")
    use_recycle_bin: bool = Field(
        default=True, description="Whether to send to Windows Recycle Bin"
    )


class DeleteFolderTool(BaseTool):
    """Tool safely deleting an entire directory folder tree (defaults to Recycle Bin)."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.delete_folder",
            name="delete_folder",
            display_name="Delete Folder",
            description="Safely deletes an entire directory folder tree. Critical risk operation.",
            category=ToolCategory.FILES,
            tags=["folder", "delete", "recycle", "filesystem"],
            input_schema=DeleteFolderInput,
            risk_level=ToolRiskLevel.CRITICAL,
            permissions=[ToolPermission.FILESYSTEM_DELETE],
            confirmation_required=True,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: DeleteFolderInput = validated_input  # type: ignore
        return self.service.delete_item(
            path_str=inp.path, use_recycle_bin=inp.use_recycle_bin
        )


# 7. Search Files Tool
class SearchFilesInput(BaseModel):
    """Input parameters for SearchFilesTool."""

    root_path: str = Field(description="Root directory path to begin search")
    pattern: str = Field(default="*", description="Filename search pattern string")
    extension: str | None = Field(
        default=None, description="Optional file extension filter (e.g. '.pdf')"
    )
    max_results: int = Field(
        default=100, ge=1, le=1000, description="Maximum search results to return"
    )
    max_depth: int = Field(
        default=5, ge=1, le=20, description="Maximum subdirectory search depth"
    )


class SearchFilesTool(BaseTool):
    """Tool recursively searching for files under a specified root directory."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.search",
            name="search",
            display_name="Search Files",
            description="Recursively searches for files matching pattern/extension under a root directory.",
            category=ToolCategory.FILES,
            tags=["search", "find", "files", "filesystem"],
            input_schema=SearchFilesInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.FILESYSTEM_SEARCH],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: SearchFilesInput = validated_input  # type: ignore
        return self.service.search(
            root_path_str=inp.root_path,
            pattern=inp.pattern,
            extension=inp.extension,
            max_results=inp.max_results,
            max_depth=inp.max_depth,
        )


# 8. Hash File Tool
class HashFileInput(BaseModel):
    """Input parameters for HashFileTool."""

    path: str = Field(description="Target file path to hash")
    algorithm: str = Field(
        default="sha256", description="Hash algorithm (sha256, md5, sha1)"
    )


class HashFileTool(BaseTool):
    """Tool calculating cryptographic SHA-256 file hash via chunked streaming."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.hash_file",
            name="hash_file",
            display_name="Hash File",
            description="Calculates cryptographic SHA-256 hash of a file using chunked streaming.",
            category=ToolCategory.FILES,
            tags=["hash", "sha256", "checksum", "filesystem"],
            input_schema=HashFileInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.FILESYSTEM_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: HashFileInput = validated_input  # type: ignore
        res = self.service.hash_file(path_str=inp.path, algorithm=inp.algorithm)
        return res.model_dump()


# 9. Compare Files Tool
class CompareFilesInput(BaseModel):
    """Input parameters for CompareFilesTool."""

    file1: str = Field(description="First file path")
    file2: str = Field(description="Second file path")


class CompareFilesTool(BaseTool):
    """Tool comparing two files by size and SHA-256 cryptographic hash."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.compare",
            name="compare",
            display_name="Compare Files",
            description="Compares two files by file size and cryptographic SHA-256 digest.",
            category=ToolCategory.FILES,
            tags=["compare", "diff", "hash", "filesystem"],
            input_schema=CompareFilesInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.FILESYSTEM_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: CompareFilesInput = validated_input  # type: ignore
        hash1 = self.service.hash_file(path_str=inp.file1)
        hash2 = self.service.hash_file(path_str=inp.file2)

        identical_size = hash1.size_bytes == hash2.size_bytes
        identical_hash = hash1.hash_value == hash2.hash_value

        return {
            "file1": hash1.path,
            "file2": hash2.path,
            "identical": identical_size and identical_hash,
            "identical_size": identical_size,
            "identical_hash": identical_hash,
            "hash1": hash1.hash_value,
            "hash2": hash2.hash_value,
        }


# 10. Workspace Information Tool
class WorkspaceInfoInput(BaseModel):
    """Input parameters for WorkspaceInfoTool."""

    path: str = Field(description="Absolute directory workspace path")


class WorkspaceInfoTool(BaseTool):
    """Tool querying aggregate metrics breakdown for a directory workspace."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.workspace_info",
            name="workspace_info",
            display_name="Get Workspace Info",
            description="Queries aggregate file count, folder count, total size, and extension breakdown for a directory.",
            category=ToolCategory.FILES,
            tags=["workspace", "summary", "folder", "filesystem"],
            input_schema=WorkspaceInfoInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.FILESYSTEM_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: WorkspaceInfoInput = validated_input  # type: ignore
        res = self.service.workspace_info(path_str=inp.path)
        return res.model_dump()


# 11. Recent Files Tool
class RecentFilesInput(BaseModel):
    """Input parameters for RecentFilesTool."""

    limit: int = Field(
        default=20, ge=1, le=100, description="Maximum recent items to return"
    )


class RecentFilesTool(BaseTool):
    """Tool querying local Windows recent files abstraction."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="files.recent",
            name="recent_files",
            display_name="Get Recent Files",
            description="Queries local Windows recent documents folder abstraction.",
            category=ToolCategory.FILES,
            tags=["recent", "history", "files", "filesystem"],
            input_schema=RecentFilesInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.FILESYSTEM_READ],
            confirmation_required=False,
            idempotent=True,
            retryable=True,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: RecentFilesInput = validated_input  # type: ignore
        recent_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent")
        items = []

        if os.path.exists(recent_dir):
            try:
                for entry in sorted(
                    os.scandir(recent_dir),
                    key=lambda e: e.stat().st_mtime,
                    reverse=True,
                ):
                    items.append({"name": entry.name, "path": entry.path})
                    if len(items) >= inp.limit:
                        break
            except Exception as exc:  # noqa: BLE001
                logger.debug(f"RecentFilesTool: Exception scanning recent items: {exc}")

        return {"count": len(items), "recent_files": items}


# 12. Batch Operation Tool
class BatchOperationInput(BaseModel):
    """Input parameters for BatchOperationTool."""

    operation_type: str = Field(
        description="Operation type: 'copy', 'move', or 'delete'"
    )
    sources: list[str] = Field(description="List of source file or folder paths")
    destination_folder: str | None = Field(
        default=None, description="Target destination directory (for copy/move)"
    )


class BatchOperationTool(BaseTool):
    """Tool executing validated multi-file batch operations."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.batch_operation",
            name="batch_operation",
            display_name="Batch File Operation",
            description="Executes validated multi-file copy, move, or delete operations with preflight checks.",
            category=ToolCategory.FILES,
            tags=["batch", "multi", "copy", "move", "delete"],
            input_schema=BatchOperationInput,
            risk_level=ToolRiskLevel.HIGH,
            permissions=[ToolPermission.FILESYSTEM_WRITE],
            confirmation_required=True,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: BatchOperationInput = validated_input  # type: ignore
        op_type = inp.operation_type.lower().strip()

        if op_type not in ("copy", "move", "delete"):
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Unsupported batch operation_type '{inp.operation_type}'. Supported: copy, move, delete.",
            )

        if op_type in ("copy", "move") and not inp.destination_folder:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Batch operation '{op_type}' requires 'destination_folder'.",
            )

        success_count = 0
        failures: list[BatchOperationFailure] = []

        for src in inp.sources:
            try:
                if op_type == "copy":
                    self.service.copy_file(src, inp.destination_folder)  # type: ignore
                elif op_type == "move":
                    self.service.move_item(src, inp.destination_folder)  # type: ignore
                elif op_type == "delete":
                    self.service.delete_item(src)
                success_count += 1
            except Exception as exc:  # noqa: BLE001
                failures.append(
                    BatchOperationFailure(
                        source_path=src,
                        destination_path=inp.destination_folder,
                        error_code="EXECUTION_FAILED",
                        reason=str(exc),
                    )
                )

        batch_res = BatchResult(
            operation_type=op_type,
            total_items=len(inp.sources),
            successful_items=success_count,
            failed_items=len(failures),
            failures=failures,
        )
        return batch_res.model_dump()
