"""High-performance local in-memory screen capture service with headless fallback."""

import io
import sys
import time

from app.automation.desktop.errors import (
    InvalidGeometryError,
    ScreenCaptureFailedError,
    WindowClosedError,
)
from app.automation.desktop.models import ScreenCaptureResult
from app.automation.desktop.monitor_manager import MonitorManager
from app.logging import logger

try:
    import mss

    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False

try:
    from PIL import Image, ImageGrab

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class ScreenCapturer:
    """High-performance in-memory local screen capture service using mss with fallback."""

    def __init__(self, monitor_manager: MonitorManager | None = None) -> None:
        self.monitor_manager = monitor_manager or MonitorManager()

    def is_available(self) -> bool:
        """Check if local screen capture backend is available."""
        return MSS_AVAILABLE or PIL_AVAILABLE

    def _create_synthetic_fallback(
        self, width: int = 1920, height: int = 1080
    ) -> bytes:
        """Generate a 1x1 or minimal PNG byte payload for headless / restricted fallback."""
        if PIL_AVAILABLE:
            img = Image.new("RGB", (width, height), color=(30, 30, 30))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        # Fallback 1x1 black PNG
        return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x009\x1e\x3d\x02\x00\x00\x00\x0cIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"

    def capture_all_monitors(self) -> ScreenCaptureResult:
        """Capture full virtual desktop spanning all monitors into in-memory PNG bytes."""
        t0 = time.perf_counter()

        # Try mss
        if MSS_AVAILABLE:
            try:
                with mss.MSS() as sct:
                    shot = sct.grab(sct.monitors[0])
                    png_bytes = mss.tools.to_png(shot.rgb, shot.size)
                    duration_ms = (time.perf_counter() - t0) * 1000.0

                    return ScreenCaptureResult(
                        status="COMPLETED",
                        image_bytes=png_bytes,
                        width=shot.width,
                        height=shot.height,
                        monitor_id=None,
                        region=(shot.left, shot.top, shot.width, shot.height),
                        timestamp=time.time(),
                        duration_ms=round(duration_ms, 2),
                    )
            except Exception as exc:
                logger.debug(f"mss screen capture failed: {exc}")

        # Try PIL ImageGrab
        if PIL_AVAILABLE:
            try:
                img = ImageGrab.grab(all_screens=True)
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                png_bytes = buf.getvalue()
                duration_ms = (time.perf_counter() - t0) * 1000.0

                return ScreenCaptureResult(
                    status="COMPLETED",
                    image_bytes=png_bytes,
                    width=img.width,
                    height=img.height,
                    monitor_id=None,
                    region=(0, 0, img.width, img.height),
                    timestamp=time.time(),
                    duration_ms=round(duration_ms, 2),
                )
            except Exception as exc:
                logger.debug(f"PIL ImageGrab screen capture failed: {exc}")

        # Headless / BitBlt Access Denied graceful fallback payload
        duration_ms = (time.perf_counter() - t0) * 1000.0
        fallback_bytes = self._create_synthetic_fallback(1920, 1080)
        return ScreenCaptureResult(
            status="HEADLESS_FALLBACK",
            image_bytes=fallback_bytes,
            width=1920,
            height=1080,
            monitor_id=None,
            region=(0, 0, 1920, 1080),
            timestamp=time.time(),
            duration_ms=round(duration_ms, 2),
        )

    def capture_monitor(self, monitor_id: int = 0) -> ScreenCaptureResult:
        """Capture specified display monitor into in-memory PNG bytes."""
        t0 = time.perf_counter()
        mon = self.monitor_manager.get_monitor_by_id(monitor_id)
        region_dict = {
            "left": mon.x,
            "top": mon.y,
            "width": mon.width,
            "height": mon.height,
        }

        if MSS_AVAILABLE:
            try:
                with mss.MSS() as sct:
                    shot = sct.grab(region_dict)
                    png_bytes = mss.tools.to_png(shot.rgb, shot.size)
                    duration_ms = (time.perf_counter() - t0) * 1000.0

                    return ScreenCaptureResult(
                        status="COMPLETED",
                        image_bytes=png_bytes,
                        width=shot.width,
                        height=shot.height,
                        monitor_id=mon.monitor_id,
                        region=(mon.x, mon.y, mon.width, mon.height),
                        timestamp=time.time(),
                        duration_ms=round(duration_ms, 2),
                    )
            except Exception as exc:
                logger.debug(f"mss monitor capture failed: {exc}")

        duration_ms = (time.perf_counter() - t0) * 1000.0
        fallback_bytes = self._create_synthetic_fallback(mon.width, mon.height)
        return ScreenCaptureResult(
            status="HEADLESS_FALLBACK",
            image_bytes=fallback_bytes,
            width=mon.width,
            height=mon.height,
            monitor_id=mon.monitor_id,
            region=(mon.x, mon.y, mon.width, mon.height),
            timestamp=time.time(),
            duration_ms=round(duration_ms, 2),
        )

    def capture_region(
        self, x: int, y: int, width: int, height: int
    ) -> ScreenCaptureResult:
        """Capture arbitrary screen bounding box region into in-memory PNG bytes."""
        if width <= 0 or height <= 0:
            raise InvalidGeometryError(
                f"Invalid region dimensions: width={width}, height={height}"
            )

        t0 = time.perf_counter()
        region_dict = {
            "left": int(x),
            "top": int(y),
            "width": int(width),
            "height": int(height),
        }

        if MSS_AVAILABLE:
            try:
                with mss.MSS() as sct:
                    shot = sct.grab(region_dict)
                    png_bytes = mss.tools.to_png(shot.rgb, shot.size)
                    duration_ms = (time.perf_counter() - t0) * 1000.0

                    return ScreenCaptureResult(
                        status="COMPLETED",
                        image_bytes=png_bytes,
                        width=shot.width,
                        height=shot.height,
                        monitor_id=None,
                        region=(int(x), int(y), int(width), int(height)),
                        timestamp=time.time(),
                        duration_ms=round(duration_ms, 2),
                    )
            except Exception as exc:
                logger.debug(f"mss region capture failed: {exc}")

        duration_ms = (time.perf_counter() - t0) * 1000.0
        fallback_bytes = self._create_synthetic_fallback(width, height)
        return ScreenCaptureResult(
            status="HEADLESS_FALLBACK",
            image_bytes=fallback_bytes,
            width=width,
            height=height,
            monitor_id=None,
            region=(int(x), int(y), int(width), int(height)),
            timestamp=time.time(),
            duration_ms=round(duration_ms, 2),
        )

    def capture_window(self, hwnd: int) -> ScreenCaptureResult:
        """Capture specified HWND window region into in-memory PNG bytes."""
        if sys.platform != "win32":
            raise ScreenCaptureFailedError(
                "Window region capture requires Windows platform."
            )

        try:
            import win32gui

            if not win32gui.IsWindow(hwnd):
                raise WindowClosedError(f"HWND {hwnd} is not a valid window.")

            rect = win32gui.GetWindowRect(hwnd)
            left, top, right, bottom = rect
            w = max(1, right - left)
            h = max(1, bottom - top)

            return self.capture_region(left, top, w, h)
        except WindowClosedError:
            raise
        except Exception as exc:
            raise ScreenCaptureFailedError(
                f"Failed to capture window HWND {hwnd}.", cause=exc
            )
