"""Unit tests for ScreenCapturer in-memory screen capture."""

from app.automation.desktop.models import ScreenCaptureResult
from app.automation.desktop.screen_capturer import ScreenCapturer


def test_capture_all_monitors_in_memory():
    capturer = ScreenCapturer()
    res = capturer.capture_all_monitors()

    assert isinstance(res, ScreenCaptureResult)
    assert res.status in ("COMPLETED", "HEADLESS_FALLBACK")
    assert res.width > 0
    assert res.height > 0
    assert res.image_bytes is not None
    assert len(res.image_bytes) > 0


def test_capture_region():
    capturer = ScreenCapturer()
    res = capturer.capture_region(0, 0, 100, 100)

    assert isinstance(res, ScreenCaptureResult)
    assert res.width == 100
    assert res.height == 100
    assert res.image_bytes is not None
