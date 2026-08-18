"""Unit tests for WindowResolver window discovery and attachment."""

import os
import sys

import pytest

from app.automation.errors import ProcessExitedError
from app.automation.models import MatchMode, WindowSearchStatus
from app.automation.uia.window_resolver import WindowResolver


def test_window_resolver_availability():
    resolver = WindowResolver()
    if sys.platform == "win32":
        assert resolver.is_available() is True
    else:
        assert resolver.is_available() is False


def test_window_enumeration():
    resolver = WindowResolver()
    if not resolver.is_available():
        pytest.skip("WindowResolver not available on host platform.")

    candidates = resolver.enumerate_windows()
    assert isinstance(candidates, list)
    if candidates:
        first = candidates[0]
        assert hasattr(first, "hwnd")
        assert hasattr(first, "title")
        assert hasattr(first, "process_id")
        assert hasattr(first, "process_name")


def test_window_resolution_by_nonexistent_hwnd():
    resolver = WindowResolver()
    if not resolver.is_available():
        pytest.skip("WindowResolver not available on host platform.")

    res = resolver.resolve_window(hwnd=99999999)
    assert res.status == WindowSearchStatus.NOT_FOUND
    assert res.selected_hwnd is None
    assert len(res.candidates) == 0


def test_window_resolution_by_nonexistent_pid():
    resolver = WindowResolver()
    if not resolver.is_available():
        pytest.skip("WindowResolver not available on host platform.")

    with pytest.raises(ProcessExitedError):
        resolver.resolve_window(process_id=9999999)


def test_window_resolution_current_process_pid():
    resolver = WindowResolver()
    if not resolver.is_available():
        pytest.skip("WindowResolver not available on host platform.")

    current_pid = os.getpid()
    res = resolver.resolve_window(process_id=current_pid, include_hidden=True)
    assert res.status in (
        WindowSearchStatus.FOUND,
        WindowSearchStatus.AMBIGUOUS,
        WindowSearchStatus.NOT_FOUND,
    )


def test_window_matching_modes():
    resolver = WindowResolver()
    assert (
        resolver._match_string(
            "Calculator - Standard", "Calculator", MatchMode.CONTAINS
        )
        is True
    )
    assert (
        resolver._match_string(
            "Calculator - Standard", "calculator", MatchMode.CASE_INSENSITIVE
        )
        is False
    )
    assert (
        resolver._match_string("Calculator", "calculator", MatchMode.CASE_INSENSITIVE)
        is True
    )
    assert (
        resolver._match_string(
            "Calculator - Standard", "Calculator", MatchMode.STARTS_WITH
        )
        is True
    )
    assert (
        resolver._match_string("Calculator - Standard", "Standard", MatchMode.EXACT)
        is False
    )
