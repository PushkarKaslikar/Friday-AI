"""Path Security Manager enforcing path resolution, path traversal prevention, and protected system path policies."""

from pathlib import Path

from app.logging import logger
from app.tools.models.errors import ToolErrorCode, ToolExecutionError

DEFAULT_PROTECTED_PATH_STRINGS: set[str] = {
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\ProgramData",
    r"C:\System Volume Information",
    r"C:\$Recycle.Bin",
}


class ProtectedPathPolicy:
    """Configurable system protected paths security policy."""

    def __init__(self, custom_protected: set[str] | None = None) -> None:
        self.protected_paths: set[Path] = set()
        paths_to_load = (
            custom_protected
            if custom_protected is not None
            else DEFAULT_PROTECTED_PATH_STRINGS
        )

        for p_str in paths_to_load:
            try:
                self.protected_paths.add(Path(p_str).resolve())
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    f"ProtectedPathPolicy: Skipping invalid path '{p_str}': {exc}"
                )

    def is_protected(self, target: Path) -> bool:
        """Evaluate if target path falls within or matches a protected system directory."""
        resolved = target.resolve()

        # Enforce protection on drive roots (e.g. C:\, D:\)
        if resolved.parent == resolved:
            return True

        for protected in self.protected_paths:
            if resolved == protected or protected in resolved.parents:
                return True

        return False


class PathSecurityManager:
    """Security manager enforcing filesystem path normalization, validation, and traversal prevention."""

    def __init__(self, policy: ProtectedPathPolicy | None = None) -> None:
        self.policy = policy or ProtectedPathPolicy()

    def normalize(self, path_str: str) -> Path:
        """Resolve absolute path, removing relative symlink traversal tokens."""
        if not path_str or not path_str.strip():
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message="Path string cannot be empty.",
            )

        try:
            return Path(path_str.strip()).resolve()
        except Exception as exc:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Failed to normalize path '{path_str}': {exc}",
            ) from exc

    def validate_path(
        self,
        path_str: str,
        must_exist: bool = False,
        must_be_file: bool = False,
        must_be_dir: bool = False,
        check_protected: bool = False,
    ) -> Path:
        """Validate and resolve target path against existence, type, and security constraints."""
        target = self.normalize(path_str)

        if must_exist and not target.exists():
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Target path '{target}' does not exist.",
            )

        if must_exist and must_be_file and not target.is_file():
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Target path '{target}' exists but is not a file.",
            )

        if must_exist and must_be_dir and not target.is_dir():
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Target path '{target}' exists but is not a directory.",
            )

        if check_protected and self.policy.is_protected(target):
            raise ToolExecutionError(
                error_code=ToolErrorCode.PERMISSION_DENIED,
                message=f"Protected System Path Policy violation: Target path '{target}' is a restricted Windows system location.",
            )

        return target

    def validate_destination(
        self,
        src_path: Path,
        dest_path: Path,
        allow_overwrite: bool = False,
        check_protected: bool = True,
    ) -> None:
        """Validate destination target against path traversal, recursive self-copy/move, and overwrite policies."""
        if check_protected and self.policy.is_protected(dest_path):
            raise ToolExecutionError(
                error_code=ToolErrorCode.PERMISSION_DENIED,
                message=f"Protected System Path Policy violation: Destination path '{dest_path}' is a restricted system location.",
            )

        if src_path == dest_path:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Source path and destination path are identical: '{src_path}'.",
            )

        # Detect recursive self-copy/move (e.g. copying C:\Folder into C:\Folder\Subfolder)
        if src_path.is_dir() and src_path in dest_path.parents:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Recursive operation error: Cannot copy or move directory '{src_path}' into its own subfolder '{dest_path}'.",
            )

        if dest_path.exists() and not allow_overwrite:
            raise ToolExecutionError(
                error_code=ToolErrorCode.PERMISSION_DENIED,
                message=f"Destination path '{dest_path}' already exists and overwrite is disabled (overwrite=false).",
            )

    def validate_filename(self, new_name: str) -> str:
        """Validate that new_name is a clean filename basename without path traversal syntax."""
        clean_name = new_name.strip()
        if not clean_name:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message="New filename cannot be empty.",
            )

        if "/" in clean_name or "\\" in clean_name or ".." in clean_name:
            raise ToolExecutionError(
                error_code=ToolErrorCode.INVALID_INPUT,
                message=f"Path traversal detected in new filename string '{new_name}'. Must be a single file name.",
            )

        return clean_name
