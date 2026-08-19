"""Windows native input execution backend using Win32 SendInput and API calls."""

import sys
import time

from app.automation.input.errors import BackendUnavailableError, InvalidKeyError
from app.automation.input.models import MouseButton
from app.logging import logger

try:
    import win32api
    import win32con
    import win32gui

    PYWIN32_AVAILABLE = True
except ImportError:
    PYWIN32_AVAILABLE = False


# Common Windows Virtual-Key Codes Mapping
VK_CODE_MAP = {
    "ctrl": 0x11,  # VK_CONTROL
    "control": 0x11,
    "lctrl": 0xA2,
    "rctrl": 0xA3,
    "alt": 0x12,  # VK_MENU
    "lalt": 0xA4,
    "ralt": 0xA5,
    "shift": 0x10,  # VK_SHIFT
    "lshift": 0xA0,
    "rshift": 0xA1,
    "win": 0x5B,  # VK_LWIN
    "cmd": 0x5B,
    "command": 0x5B,
    "enter": 0x0D,  # VK_RETURN
    "return": 0x0D,
    "esc": 0x1B,  # VK_ESCAPE
    "escape": 0x1B,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "back": 0x08,
    "delete": 0x2E,
    "del": 0x2E,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "capslock": 0x14,
    "insert": 0x2D,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}

# Add letter keys A-Z and digits 0-9
for char in "abcdefghijklmnopqrstuvwxyz":
    VK_CODE_MAP[char] = ord(char.upper())
for digit in "0123456789":
    VK_CODE_MAP[digit] = ord(digit)


class NativeInputBackend:
    """Windows-native input backend using win32api, win32con, and SendInput."""

    def __init__(self) -> None:
        self._held_modifiers: set[int] = set()
        self._held_buttons: set[MouseButton] = set()

    def is_available(self) -> bool:
        """Check if native Win32 input APIs are available."""
        return sys.platform == "win32" and PYWIN32_AVAILABLE

    def get_vk_code(self, key_name: str) -> int:
        """Resolve string key identifier to Windows Virtual Key code."""
        if not key_name:
            raise InvalidKeyError("Empty key identifier supplied.")

        clean_name = str(key_name).strip().lower()
        if clean_name in VK_CODE_MAP:
            return VK_CODE_MAP[clean_name]

        if len(clean_name) == 1:
            return ord(clean_name.upper())

        raise InvalidKeyError(f"Unsupported key identifier: '{key_name}'")

    def move_to(self, x: int, y: int) -> None:
        """Set absolute mouse cursor position."""
        if not self.is_available():
            raise BackendUnavailableError("Native Windows input backend unavailable.")
        try:
            win32api.SetCursorPos((int(x), int(y)))
        except Exception as exc:
            logger.error(f"Native move_to failed for ({x}, {y}): {exc}")

    def click(
        self,
        x: int,
        y: int,
        button: MouseButton = MouseButton.LEFT,
        click_count: int = 1,
    ) -> None:
        """Execute mouse click at specified coordinates."""
        if not self.is_available():
            raise BackendUnavailableError("Native Windows input backend unavailable.")

        self.move_to(x, y)
        down_flag, up_flag = self._get_mouse_flags(button)

        for _ in range(click_count):
            win32api.mouse_event(down_flag, int(x), int(y), 0, 0)
            time.sleep(0.01)
            win32api.mouse_event(up_flag, int(x), int(y), 0, 0)
            if click_count > 1:
                time.sleep(0.05)

    def mouse_down(
        self, x: int, y: int, button: MouseButton = MouseButton.LEFT
    ) -> None:
        """Send mouse down event."""
        if not self.is_available():
            raise BackendUnavailableError("Native Windows input backend unavailable.")
        self.move_to(x, y)
        down_flag, _ = self._get_mouse_flags(button)
        win32api.mouse_event(down_flag, int(x), int(y), 0, 0)
        self._held_buttons.add(button)

    def mouse_up(self, x: int, y: int, button: MouseButton = MouseButton.LEFT) -> None:
        """Send mouse up event."""
        if not self.is_available():
            raise BackendUnavailableError("Native Windows input backend unavailable.")
        self.move_to(x, y)
        _, up_flag = self._get_mouse_flags(button)
        win32api.mouse_event(up_flag, int(x), int(y), 0, 0)
        self._held_buttons.discard(button)

    def key_down(self, key_name: str) -> None:
        """Send key down event for specified key."""
        if not self.is_available():
            raise BackendUnavailableError("Native Windows input backend unavailable.")
        vk = self.get_vk_code(key_name)
        win32api.keybd_event(vk, 0, 0, 0)
        self._held_modifiers.add(vk)

    def key_up(self, key_name: str) -> None:
        """Send key up event for specified key."""
        if not self.is_available():
            raise BackendUnavailableError("Native Windows input backend unavailable.")
        vk = self.get_vk_code(key_name)
        win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
        self._held_modifiers.discard(vk)

    def press_key(self, key_name: str) -> None:
        """Execute key down followed by key up."""
        self.key_down(key_name)
        time.sleep(0.01)
        self.key_up(key_name)

    def press_hotkey(self, keys: list[str]) -> None:
        """Execute key combination with safe modifier release cleanup."""
        if not keys:
            return
        vks = [self.get_vk_code(k) for k in keys]
        try:
            for vk in vks:
                win32api.keybd_event(vk, 0, 0, 0)
                self._held_modifiers.add(vk)
                time.sleep(0.01)
            time.sleep(0.05)
        finally:
            for vk in reversed(vks):
                win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
                self._held_modifiers.discard(vk)

    def type_text_unicode(self, text: str, interval_sec: float = 0.05) -> None:
        """Send text typing using Win32 SendInput KEYEVENTF_UNICODE for Unicode safety."""
        if not self.is_available():
            raise BackendUnavailableError("Native Windows input backend unavailable.")
        if not text:
            return

        for char in text:
            # Send character via SendInput Unicode event
            self._send_unicode_char(char)
            if interval_sec > 0:
                time.sleep(interval_sec)

    def release_all_inputs(self) -> None:
        """Emergency release of all held mouse buttons and modifier keys."""
        if not self.is_available():
            return

        x, y = 0, 0
        try:
            x, y = win32api.GetCursorPos()
        except Exception:
            pass

        # Release mouse buttons
        for btn in list(self._held_buttons) or [
            MouseButton.LEFT,
            MouseButton.RIGHT,
            MouseButton.MIDDLE,
        ]:
            _, up_flag = self._get_mouse_flags(btn)
            try:
                win32api.mouse_event(up_flag, int(x), int(y), 0, 0)
            except Exception:
                pass
        self._held_buttons.clear()

        # Release modifier keys
        modifiers = list(self._held_modifiers) or [
            0x10,
            0x11,
            0x12,
            0x5B,
        ]  # Shift, Ctrl, Alt, Win
        for vk in modifiers:
            try:
                win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
            except Exception:
                pass
        self._held_modifiers.clear()

    def _get_mouse_flags(self, button: MouseButton) -> tuple[int, int]:
        """Return (down_flag, up_flag) for win32api mouse_event."""
        if button == MouseButton.RIGHT:
            return win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP
        elif button == MouseButton.MIDDLE:
            return win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP
        return win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP

    def _send_unicode_char(self, char: str) -> None:
        """Helper to dispatch single Unicode character via SendInput."""
        ord_val = ord(char)
        # Use keybd_event with KEYEVENTF_UNICODE
        win32api.keybd_event(0, ord_val, win32con.KEYEVENTF_UNICODE, 0)
        win32api.keybd_event(
            0, ord_val, win32con.KEYEVENTF_UNICODE | win32con.KEYEVENTF_KEYUP, 0
        )
