"""Unit tests for SensitiveDataSanitizer."""

from app.tools.execution.result_normalizer import SensitiveDataSanitizer


def test_sensitive_data_sanitizer_masks_secrets():
    payload = {
        "user": "pushkar",
        "password": "supersecretpassword123",
        "api_key": "sk-proj-123456",
        "nested": {
            "token": "bearer_xyz_789",
            "normal_field": "hello",
        },
    }

    sanitized = SensitiveDataSanitizer.sanitize(payload)

    assert sanitized["user"] == "pushkar"
    assert sanitized["password"] == "********"
    assert sanitized["api_key"] == "********"
    assert sanitized["nested"]["token"] == "********"
    assert sanitized["nested"]["normal_field"] == "hello"
