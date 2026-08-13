"""Structured Pydantic models for filesystem entries, search results, and batch operations."""

from pydantic import BaseModel, Field


class DirectoryEntry(BaseModel):
    """Model representing a single file or directory item."""

    name: str = Field(description="Basename of the entry")
    path: str = Field(description="Absolute path of the entry")
    is_directory: bool = Field(description="True if entry is a directory")
    size_bytes: int = Field(default=0, description="Size in bytes")
    created_time: str = Field(default="", description="Creation timestamp ISO string")
    modified_time: str = Field(
        default="", description="Modification timestamp ISO string"
    )
    extension: str = Field(default="", description="File extension with leading dot")
    is_hidden: bool = Field(default=False, description="True if hidden attribute set")
    is_readonly: bool = Field(
        default=False, description="True if read-only attribute set"
    )


class FileHashResult(BaseModel):
    """Model representing cryptographic file hash output."""

    path: str = Field(description="Absolute file path")
    algorithm: str = Field(description="Hash algorithm (e.g. SHA-256)")
    hash_value: str = Field(description="Hexadecimal digest string")
    size_bytes: int = Field(description="File size in bytes")


class WorkspaceSummary(BaseModel):
    """High-level summary breakdown of a workspace directory."""

    path: str = Field(description="Absolute root directory path")
    file_count: int = Field(default=0, description="Total number of files")
    folder_count: int = Field(default=0, description="Total number of subdirectories")
    total_size_bytes: int = Field(default=0, description="Cumulative size in bytes")
    total_size_mb: float = Field(default=0.0, description="Cumulative size in MB")
    extension_counts: dict[str, int] = Field(
        default_factory=dict, description="Breakdown of file count by extension"
    )


class BatchOperationFailure(BaseModel):
    """Model representing a single item failure within a batch operation."""

    source_path: str = Field(description="Source path that failed")
    destination_path: str | None = Field(
        default=None, description="Target destination path if applicable"
    )
    error_code: str = Field(description="Error classification code")
    reason: str = Field(description="Detailed failure reason")


class BatchResult(BaseModel):
    """Aggregated result output for batch filesystem operations."""

    operation_type: str = Field(
        description="Type of batch operation (copy, move, delete)"
    )
    total_items: int = Field(default=0, description="Total requested items")
    successful_items: int = Field(
        default=0, description="Count of successfully processed items"
    )
    failed_items: int = Field(default=0, description="Count of failed items")
    skipped_items: int = Field(default=0, description="Count of skipped items")
    failures: list[BatchOperationFailure] = Field(
        default_factory=list, description="List of individual item failures"
    )

    @property
    def is_complete_success(self) -> bool:
        return self.failed_items == 0 and self.successful_items == self.total_items
