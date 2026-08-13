"""Unit tests for UrlSecurityManager."""

import pytest

from app.platform.browser.url_security import UrlSecurityManager
from app.tools.models.errors import ToolErrorCode, ToolExecutionError


def test_url_security_sanitize_valid():
    sec = UrlSecurityManager()
    assert sec.sanitize_url("https://youtube.com") == "https://youtube.com"
    assert sec.sanitize_url("google.com/search") == "https://google.com/search"


def test_url_security_reject_dangerous_schemes():
    sec = UrlSecurityManager()

    with pytest.raises(ToolExecutionError) as exc_info:
        sec.sanitize_url("javascript:alert(1)")
    assert exc_info.value.error_code == ToolErrorCode.PERMISSION_DENIED

    with pytest.raises(ToolExecutionError) as exc_info:
        sec.sanitize_url("data:text/html,<h1>Hacked</h1>")
    assert exc_info.value.error_code == ToolErrorCode.PERMISSION_DENIED


def test_url_security_is_safe_url():
    sec = UrlSecurityManager()
    assert sec.is_safe_url("https://python.org") is True
    assert sec.is_safe_url("file:///C:/secret.txt") is False
