"""Target resolver for validating multi-monitor virtual screen coordinates and UIA targets."""

import sys

from app.automation.input.errors import InvalidCoordinatesError, InvalidTargetError
from app.automation.input.models import InputTarget, MousePosition, TargetType
from app.logging import logger

try:
    import win32api
    import win32gui

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


class TargetResolver:
    """Resolves and validates input targets against Windows multi-monitor virtual desktop bounds."""

    def __init__(self, bounds_check_enabled: bool = True) -> None:
        self.bounds_check_enabled = bounds_check_enabled

    def get_virtual_screen_bounds(self) -> tuple[int, int, int, int]:
        """Get virtual desktop screen bounds (x_min, y_min, x_max, y_max)."""
        if sys.platform == "win32" and PYWIN32_AVAILABLE:
            try:
                x_min = win32api.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
                y_min = win32api.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
                width = win32api.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
                height = win32api.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
                return x_min, y_min, x_min + width - 1, y_min + height - 1
            except Exception as exc:
                logger.debug(f"Failed to query Win32 virtual screen metrics: {exc}")

        # Default single monitor fallback bounds (1920x1080)
        return 0, 0, 1919, 1079

    def validate_coordinates(self, x: int, y: int) -> bool:
        """Verify coordinates lie within valid virtual screen bounds."""
        if not self.bounds_check_enabled:
            return True

        x_min, y_min, x_max, y_max = self.get_virtual_screen_bounds()
        if x < x_min or x > x_max or y < y_min or y > y_max:
            raise InvalidCoordinatesError(
                f"Coordinates ({x}, {y}) lie outside virtual screen bounds ({x_min},{y_min}) to ({x_max},{y_max}).",
                details={
                    "x": x,
                    "y": y,
                    "bounds": {
                        "x_min": x_min,
                        "y_min": y_min,
                        "x_max": x_max,
                        "y_max": y_max,
                    },
                },
            )
        return True

    def resolve_target(self, target: InputTarget) -> MousePosition:
        """Resolve InputTarget payload to valid MousePosition screen coordinates."""
        if target is None:
            raise InvalidTargetError("InputTarget is None.")

        if target.target_type == TargetType.SCREEN_COORDINATE:
            if target.x is None or target.y is None:
                raise InvalidTargetError(
                    "TargetType.SCREEN_COORDINATE requires both x and y coordinates."
                )
            self.validate_coordinates(target.x, target.y)
            return MousePosition(x=target.x, y=target.y)

        elif target.target_type == TargetType.UIA_ELEMENT:
            elem = target.element
            if elem is None:
                raise InvalidTargetError(
                    "TargetType.UIA_ELEMENT target requires element instance."
                )
            if not elem.is_enabled:
                raise InvalidTargetError(
                    f"Target UIA element '{elem.name}' ({elem.control_type}) is disabled.",
                    details={"element_id": elem.element_id},
                )
            if not elem.bounding_rectangle:
                raise InvalidTargetError(
                    f"Target UIA element '{elem.name}' has no valid bounding rectangle.",
                    details={"element_id": elem.element_id},
                )

            rect = elem.bounding_rectangle
            center_x = rect.left + (rect.width // 2)
            center_y = rect.top + (rect.height // 2)
            self.validate_coordinates(center_x, center_y)
            return MousePosition(x=center_x, y=center_y)

        elif target.target_type == TargetType.WINDOW:
            hwnd = target.window_handle
            if not hwnd or hwnd <= 0:
                raise InvalidTargetError(f"Invalid HWND handle: {hwnd}")
            if sys.platform == "win32" and PYWIN32_AVAILABLE:
                try:
                    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                    center_x = left + ((right - left) // 2)
                    center_y = top + ((bottom - top) // 2)
                    self.validate_coordinates(center_x, center_y)
                    return MousePosition(x=center_x, y=center_y)
                except Exception as exc:
                    raise InvalidTargetError(
                        f"Could not get window rect for HWND {hwnd}", cause=exc
                    )
            raise InvalidTargetError(
                "Native window rect query unavailable on host platform."
            )

        raise InvalidTargetError(f"Unsupported target_type: {target.target_type}")
