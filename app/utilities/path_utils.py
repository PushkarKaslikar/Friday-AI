"""Path utility functions for path resolution, normalization, and directory management."""

from pathlib import Path


def ensure_directory_exists(directory_path: str | Path) -> Path:
    """Ensure that a directory exists, creating parent directories if necessary.

    Args:
        directory_path: Directory path as string or Path object.

    Returns:
        Resolved absolute Path object of the directory.
    """
    path = Path(directory_path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_path_readable(path: str | Path) -> bool:
    """Check if a file or directory exists and is readable."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        if p.is_file():
            with open(p, "rb") as f:
                f.read(1)
        elif p.is_dir():
            next(p.iterdir(), None)
        return True
    except (PermissionError, OSError):
        return False


def is_directory_writable(directory_path: str | Path) -> bool:
    """Check if a directory exists (or can be created) and is writable."""
    path = ensure_directory_exists(directory_path)
    test_file = path / ".write_test_tmp"
    try:
        test_file.touch(exist_ok=True)
        test_file.unlink(missing_ok=True)
        return True
    except (PermissionError, OSError):
        return False
