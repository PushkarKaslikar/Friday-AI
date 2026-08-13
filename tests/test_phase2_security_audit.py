"""Security audit test suite validating path security, URL validation, default deny, sensitive data masking, and parameter fuzzing."""

import pytest

from app.bootstrap.bootstrapper import AppBootstrapper
from app.platform.browser.url_security import UrlSecurityManager
from app.platform.filesystem.path_security import PathSecurityManager
from app.tools.execution.result_normalizer import SensitiveDataSanitizer
from app.tools.execution.tool_executor import ToolExecutor
from app.tools.models.errors import ToolErrorCode, ToolExecutionError
from app.tools.models.request import ToolRequest


@pytest.fixture(scope="module")
def app_bootstrap():
    """Module-level fixture initializing full application container."""
    bootstrapper = AppBootstrapper()
    return bootstrapper.run()


def test_security_protected_system_paths():
    """Verify PathSecurityManager rejects restricted Windows system directories."""
    path_sec = PathSecurityManager()

    restricted_paths = [
        r"C:\Windows",
        r"C:\Windows\System32",
        r"C:\Program Files",
        r"C:\Program Files (x86)",
        r"C:\ProgramData",
    ]

    for p in restricted_paths:
        with pytest.raises(ToolExecutionError) as exc_info:
            path_sec.validate_path(p, check_protected=True)
        assert exc_info.value.error_code == ToolErrorCode.PERMISSION_DENIED


def test_security_path_traversal_prevention():
    """Verify path traversal tokens ('..') are resolved and validated against destination boundaries."""
    path_sec = PathSecurityManager()

    with pytest.raises(ToolExecutionError) as exc_info:
        path_sec.validate_filename("../secret.txt")
    assert exc_info.value.error_code == ToolErrorCode.INVALID_INPUT

    with pytest.raises(ToolExecutionError) as exc_info:
        path_sec.validate_filename("folder\\..\\file.exe")
    assert exc_info.value.error_code == ToolErrorCode.INVALID_INPUT


def test_security_dangerous_url_schemes():
    """Verify UrlSecurityManager strictly rejects non-web and script-injection URL schemes."""
    url_sec = UrlSecurityManager()

    dangerous_urls = [
        "javascript:alert(document.cookie)",
        "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==",
        "vbscript:msgbox(1)",
        "file:///C:/Windows/System32/cmd.exe",
    ]

    for u in dangerous_urls:
        with pytest.raises(ToolExecutionError) as exc_info:
            url_sec.sanitize_url(u)
        assert exc_info.value.error_code in (
            ToolErrorCode.PERMISSION_DENIED,
            ToolErrorCode.INVALID_INPUT,
        )


def test_security_sensitive_data_masking():
    """Verify SensitiveDataSanitizer masks tokens, passwords, and API keys."""
    payload = {
        "user": "pushkar",
        "password": "SuperSecretPassword123",
        "access_token": "bearer_abc123xyz789",
        "api_key": "sk_live_999888777",
        "nested": {
            "secret": "MyPrivateData",
            "normal_data": "Public Information",
        },
    }

    sanitized = SensitiveDataSanitizer.sanitize(payload)
    assert sanitized["password"] == "********"
    assert sanitized["access_token"] == "********"
    assert sanitized["api_key"] == "********"
    assert sanitized["nested"]["secret"] == "********"
    assert sanitized["nested"]["normal_data"] == "Public Information"


def test_security_input_fuzzing(app_bootstrap):
    """Verify invalid parameter types and malformed inputs produce structured errors without app crash."""
    container = app_bootstrap.container
    executor: ToolExecutor = container.tool_executor()

    # 1. Non-existent tool ID
    res_bad_id = executor.execute_request(
        ToolRequest(tool_id="system.invalid_nonexistent_tool", arguments={})
    )
    assert res_bad_id.success is False
    assert res_bad_id.error_code == ToolErrorCode.TOOL_NOT_FOUND

    # 2. Missing mandatory parameters
    res_missing_param = executor.execute_request(
        ToolRequest(tool_id="files.open_file", arguments={})
    )
    assert res_missing_param.success is False
    assert res_missing_param.error_code == ToolErrorCode.INVALID_INPUT

    # 3. Invalid parameter types
    res_invalid_type = executor.execute_request(
        ToolRequest(
            tool_id="browser.get_page_text", arguments={"max_length": "not_an_int"}
        )
    )
    assert res_invalid_type.success is False
    assert res_invalid_type.error_code == ToolErrorCode.INVALID_INPUT
