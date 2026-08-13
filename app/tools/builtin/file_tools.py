"""File and Folder system tools for inspecting, creating, copying, and calculating size of files and directories."""

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.platform.filesystem.filesystem_service import FilesystemService
from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.base.tool import BaseTool
from app.tools.categories import ToolCategory
from app.tools.models.errors import ToolErrorCode, ToolExecutionError


# 1. Open File Tool
class OpenFileInput(BaseModel):
    """Input parameters for OpenFileTool."""

    path: str = Field(
        description="Absolute file path to open in Windows default application"
    )


class OpenFileTool(BaseTool):
    """Tool opening a file using Windows default associated application."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="files.open_file",
            name="open_file",
            display_name="Open File",
            description="Opens a file path in its associated Windows default application.",
            category=ToolCategory.FILES,
            tags=["file", "open", "launch", "filesystem"],
            input_schema=OpenFileInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.FILESYSTEM_READ],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: OpenFileInput = validated_input  # type: ignore
        file_path = Path(inp.path).resolve()

        if not file_path.exists() or not file_path.is_file():
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"File path '{file_path}' does not exist or is not a valid file.",
                tool_id=self.tool_id,
            )

        try:
            os.startfile(str(file_path))
            return {"opened": True, "path": str(file_path)}
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to open file '{file_path}': {exc}",
                tool_id=self.tool_id,
            ) from exc


# 2. Open Folder Tool
class OpenFolderInput(BaseModel):
    """Input parameters for OpenFolderTool."""

    path: str = Field(description="Absolute directory path to open in Windows Explorer")


class OpenFolderTool(BaseTool):
    """Tool opening a folder path in Windows Explorer."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="files.open_folder",
            name="open_folder",
            display_name="Open Folder",
            description="Opens a directory path in Windows Explorer.",
            category=ToolCategory.FILES,
            tags=["folder", "directory", "explorer", "filesystem"],
            input_schema=OpenFolderInput,
            risk_level=ToolRiskLevel.LOW,
            permissions=[ToolPermission.FILESYSTEM_READ],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: OpenFolderInput = validated_input  # type: ignore
        folder_path = Path(inp.path).resolve()

        if not folder_path.exists() or not folder_path.is_dir():
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Folder path '{folder_path}' does not exist or is not a directory.",
                tool_id=self.tool_id,
            )

        try:
            subprocess.Popen(["explorer.exe", str(folder_path)], close_fds=True)
            return {"opened": True, "path": str(folder_path)}
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.EXECUTION_FAILED,
                message=f"Failed to open folder '{folder_path}': {exc}",
                tool_id=self.tool_id,
            ) from exc


# 3. File Exists Tool
class FileExistsInput(BaseModel):
    """Input parameters for FileExistsTool."""

    path: str = Field(description="Target file path")


class FileExistsTool(BaseTool):
    """Tool checking whether a file exists."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="files.file_exists",
            name="file_exists",
            display_name="Check File Existence",
            description="Checks if a target file exists on disk.",
            category=ToolCategory.FILES,
            tags=["file", "exists", "filesystem"],
            input_schema=FileExistsInput,
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
        inp: FileExistsInput = validated_input  # type: ignore
        target = Path(inp.path).resolve()
        exists = target.exists() and target.is_file()
        return {"path": str(target), "exists": exists}


# 4. Folder Exists Tool
class FolderExistsInput(BaseModel):
    """Input parameters for FolderExistsTool."""

    path: str = Field(description="Target folder directory path")


class FolderExistsTool(BaseTool):
    """Tool checking whether a directory folder exists."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="files.folder_exists",
            name="folder_exists",
            display_name="Check Folder Existence",
            description="Checks if a target directory folder exists on disk.",
            category=ToolCategory.FILES,
            tags=["folder", "exists", "filesystem"],
            input_schema=FolderExistsInput,
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
        inp: FolderExistsInput = validated_input  # type: ignore
        target = Path(inp.path).resolve()
        exists = target.exists() and target.is_dir()
        return {"path": str(target), "exists": exists}


# 5. File Information Tool
class FileInfoInput(BaseModel):
    """Input parameters for FileInfoTool."""

    path: str = Field(description="Absolute file path")


class FileInfoTool(BaseTool):
    """Tool querying file metadata timestamps and size."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="files.get_file_info",
            name="get_file_info",
            display_name="Get File Metadata",
            description="Queries file size, extension, created time, modified time, and absolute path.",
            category=ToolCategory.FILES,
            tags=["file", "info", "metadata", "filesystem"],
            input_schema=FileInfoInput,
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
        inp: FileInfoInput = validated_input  # type: ignore
        target = Path(inp.path).resolve()

        if not target.exists() or not target.is_file():
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"File '{target}' does not exist or is not a file.",
                tool_id=self.tool_id,
            )

        stat = target.stat()
        fmt_time = lambda ts: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

        return {
            "filename": target.name,
            "extension": target.suffix,
            "path": str(target),
            "size_bytes": stat.st_size,
            "size_kb": round(stat.st_size / 1024, 2),
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_time": fmt_time(stat.st_ctime),
            "modified_time": fmt_time(stat.st_mtime),
            "accessed_time": fmt_time(stat.st_atime),
        }


# 6. Folder Information Tool
class FolderInfoInput(BaseModel):
    """Input parameters for FolderInfoTool."""

    path: str = Field(description="Absolute folder directory path")


class FolderInfoTool(BaseTool):
    """Tool querying directory contents summary metadata."""

    def __init__(self) -> None:
        meta = ToolMetadata(
            tool_id="files.get_folder_info",
            name="get_folder_info",
            display_name="Get Folder Metadata",
            description="Queries directory folder timestamps, file count, and subdirectory count.",
            category=ToolCategory.FILES,
            tags=["folder", "info", "metadata", "filesystem"],
            input_schema=FolderInfoInput,
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
        inp: FolderInfoInput = validated_input  # type: ignore
        target = Path(inp.path).resolve()

        if not target.exists() or not target.is_dir():
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Folder '{target}' does not exist or is not a directory.",
                tool_id=self.tool_id,
            )

        stat = target.stat()
        fmt_time = lambda ts: time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))

        file_count = 0
        dir_count = 0
        try:
            for item in target.iterdir():
                if item.is_file():
                    file_count += 1
                elif item.is_dir():
                    dir_count += 1
        except PermissionError:
            pass

        return {
            "folder_name": target.name,
            "path": str(target),
            "file_count": file_count,
            "subdirectory_count": dir_count,
            "created_time": fmt_time(stat.st_ctime),
            "modified_time": fmt_time(stat.st_mtime),
        }


# 7. Create File Tool
class CreateFileInput(BaseModel):
    """Input parameters for CreateFileTool."""

    path: str = Field(description="Target file path to create")
    content: str = Field(default="", description="Optional UTF-8 text string content")
    overwrite: bool = Field(
        default=False, description="Whether to allow overwriting an existing file"
    )


class CreateFileTool(BaseTool):
    """Tool creating a new file with optional content."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.create_file",
            name="create_file",
            display_name="Create File",
            description="Creates a new file with optional UTF-8 content.",
            category=ToolCategory.FILES,
            tags=["file", "create", "write", "filesystem"],
            input_schema=CreateFileInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.FILESYSTEM_CREATE],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: CreateFileInput = validated_input  # type: ignore
        return self.service.create_file(
            path_str=inp.path, content=inp.content, overwrite=inp.overwrite
        )


# 8. Create Folder Tool
class CreateFolderInput(BaseModel):
    """Input parameters for CreateFolderTool."""

    path: str = Field(description="Target directory folder path to create")


class CreateFolderTool(BaseTool):
    """Tool creating a single or nested directory folder structure."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.create_folder",
            name="create_folder",
            display_name="Create Folder",
            description="Creates a single or nested directory folder structure.",
            category=ToolCategory.FILES,
            tags=["folder", "create", "mkdir", "filesystem"],
            input_schema=CreateFolderInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.FILESYSTEM_CREATE],
            confirmation_required=False,
            idempotent=True,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: CreateFolderInput = validated_input  # type: ignore
        return self.service.create_folder(path_str=inp.path)


# 9. Copy File Tool
class CopyFileInput(BaseModel):
    """Input parameters for CopyFileTool."""

    source: str = Field(description="Source file path")
    destination: str = Field(description="Target destination file or directory path")
    overwrite: bool = Field(
        default=False, description="Whether to allow overwriting destination"
    )


class CopyFileTool(BaseTool):
    """Tool copying a file from source to destination."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.copy_file",
            name="copy_file",
            display_name="Copy File",
            description="Copies a single file from source to destination.",
            category=ToolCategory.FILES,
            tags=["file", "copy", "filesystem"],
            input_schema=CopyFileInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.FILESYSTEM_COPY],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: CopyFileInput = validated_input  # type: ignore
        return self.service.copy_file(
            src_str=inp.source, dest_str=inp.destination, overwrite=inp.overwrite
        )


# 10. Copy Folder Tool
class CopyFolderInput(BaseModel):
    """Input parameters for CopyFolderTool."""

    source: str = Field(description="Source directory folder path")
    destination: str = Field(description="Target destination directory path")
    overwrite: bool = Field(
        default=False, description="Whether to allow overwriting files in destination"
    )


class CopyFolderTool(BaseTool):
    """Tool copying an entire directory folder tree with self-copy protection."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.copy_folder",
            name="copy_folder",
            display_name="Copy Folder",
            description="Copies an entire directory folder tree with self-copy prevention.",
            category=ToolCategory.FILES,
            tags=["folder", "copy", "filesystem"],
            input_schema=CopyFolderInput,
            risk_level=ToolRiskLevel.MEDIUM,
            permissions=[ToolPermission.FILESYSTEM_COPY],
            confirmation_required=False,
            idempotent=False,
        )
        super().__init__(metadata=meta)
        self.service = service or FilesystemService()

    def run_tool(
        self, validated_input: BaseModel, command_id: str = ""
    ) -> dict[str, Any]:
        inp: CopyFolderInput = validated_input  # type: ignore
        return self.service.copy_folder(
            src_str=inp.source, dest_str=inp.destination, overwrite=inp.overwrite
        )


# 11. List Directory Tool
class ListDirectoryInput(BaseModel):
    """Input parameters for ListDirectoryTool."""

    path: str = Field(description="Target directory path")
    recursive: bool = Field(
        default=False, description="Whether to recursively scan subdirectories"
    )
    include_hidden: bool = Field(
        default=False, description="Whether to include hidden files"
    )


class ListDirectoryTool(BaseTool):
    """Tool listing contents inside a target directory folder."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.list_directory",
            name="list_directory",
            display_name="List Directory Contents",
            description="Lists file and directory entries inside a target directory folder.",
            category=ToolCategory.FILES,
            tags=["folder", "list", "dir", "filesystem"],
            input_schema=ListDirectoryInput,
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
        inp: ListDirectoryInput = validated_input  # type: ignore
        entries = self.service.list_directory(
            path_str=inp.path,
            recursive=inp.recursive,
            include_hidden=inp.include_hidden,
        )
        return {
            "path": inp.path,
            "count": len(entries),
            "entries": [e.model_dump() for e in entries],
        }


# 12. Calculate Size Tool
class CalculateSizeInput(BaseModel):
    """Input parameters for CalculateSizeTool."""

    path: str = Field(description="Target file or directory path")


class CalculateSizeTool(BaseTool):
    """Tool calculating recursive size of a file or directory folder."""

    def __init__(self, service: FilesystemService | None = None) -> None:
        meta = ToolMetadata(
            tool_id="files.calculate_size",
            name="calculate_size",
            display_name="Calculate Size",
            description="Calculates cumulative size of a target file or directory folder.",
            category=ToolCategory.FILES,
            tags=["size", "disk", "bytes", "filesystem"],
            input_schema=CalculateSizeInput,
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
        inp: CalculateSizeInput = validated_input  # type: ignore
        summary = self.service.workspace_info(path_str=inp.path)
        return {
            "path": summary.path,
            "total_bytes": summary.total_size_bytes,
            "total_mb": summary.total_size_mb,
            "file_count": summary.file_count,
            "folder_count": summary.folder_count,
        }
