"""Unit tests for utilities module."""

from pathlib import Path

import pytest

from app.exceptions.config import ConfigurationError
from app.utilities import (
    ensure_directory_exists,
    is_directory_writable,
    is_path_readable,
    is_python_version_supported,
    read_json_file,
    validate_non_empty_string,
    validate_positive_integer,
    write_json_file,
)


def test_path_utilities(tmp_path: Path):
    test_dir = tmp_path / "nested" / "dir"
    created_dir = ensure_directory_exists(test_dir)
    assert created_dir.exists()
    assert is_directory_writable(created_dir)

    dummy_file = created_dir / "test.txt"
    dummy_file.write_text("hello", encoding="utf-8")
    assert is_path_readable(dummy_file)


def test_file_utilities(tmp_path: Path):
    json_path = tmp_path / "data.json"
    data = {"key": "value", "number": 42}
    write_json_file(json_path, data)
    assert json_path.exists()

    loaded = read_json_file(json_path)
    assert loaded == data


def test_file_utilities_invalid_json(tmp_path: Path):
    bad_json = tmp_path / "bad.json"
    bad_json.write_text("invalid json string", encoding="utf-8")
    with pytest.raises(ConfigurationError):
        read_json_file(bad_json)


def test_system_utilities():
    assert is_python_version_supported() is True


def test_validation_utilities():
    assert validate_non_empty_string("hello", "field") == "hello"
    with pytest.raises(ValueError):
        validate_non_empty_string("   ", "field")

    assert validate_positive_integer(10, "count") == 10
    with pytest.raises(ValueError):
        validate_positive_integer(0, "count")
