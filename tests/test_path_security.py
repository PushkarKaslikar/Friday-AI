"""Unit tests for PathSecurityManager and ProtectedPathPolicy."""

from pathlib import Path

import pytest

from app.platform.filesystem.path_security import (
    PathSecurityManager,
    ProtectedPathPolicy,
)
from app.tools.models.errors import ToolErrorCode, ToolExecutionError


def test_protected_path_policy():
    policy = ProtectedPathPolicy(custom_protected={r"C:\Windows", r"C:\Program Files"})
    assert policy.is_protected(Path(r"C:\Windows\System32\cmd.exe")) is True
    assert policy.is_protected(Path(r"C:\Program Files\App\exe.exe")) is True
    assert policy.is_protected(Path(r"C:\Users\Pushkar\Documents")) is False


def test_path_security_normalize():
    sec = PathSecurityManager()
    path = sec.normalize(r"C:\Users\Pushkar\..\Pushkar\Documents")
    assert ".." not in str(path)
    assert path.name == "Documents"


def test_path_security_validate_protected():
    sec = PathSecurityManager()
    with pytest.raises(ToolExecutionError) as exc_info:
        sec.validate_path(r"C:\Windows\System32\config", check_protected=True)
    assert exc_info.value.error_code == ToolErrorCode.PERMISSION_DENIED


def test_path_security_recursive_self_copy_prevention(tmp_path):
    sec = PathSecurityManager()
    src_dir = tmp_path / "SourceDir"
    src_dir.mkdir()
    sub_dir = src_dir / "SubDir"

    with pytest.raises(ToolExecutionError) as exc_info:
        sec.validate_destination(src_dir, sub_dir)
    assert exc_info.value.error_code == ToolErrorCode.INVALID_INPUT
    assert "Recursive operation error" in exc_info.value.message


def test_path_security_filename_traversal():
    sec = PathSecurityManager()
    assert sec.validate_filename("valid_name.txt") == "valid_name.txt"

    with pytest.raises(ToolExecutionError) as exc_info:
        sec.validate_filename(r"..\..\etc\passwd")
    assert exc_info.value.error_code == ToolErrorCode.INVALID_INPUT
