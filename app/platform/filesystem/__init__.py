"""Filesystem engine package providing security, streaming file operations, search, and workspace metrics."""

from app.platform.filesystem.filesystem_service import FilesystemService
from app.platform.filesystem.models import (
    BatchResult,
    DirectoryEntry,
    FileHashResult,
    WorkspaceSummary,
)
from app.platform.filesystem.path_security import (
    PathSecurityManager,
    ProtectedPathPolicy,
)

__all__ = [
    "BatchResult",
    "DirectoryEntry",
    "FileHashResult",
    "FilesystemService",
    "PathSecurityManager",
    "ProtectedPathPolicy",
    "WorkspaceSummary",
]
