"""PyAutoGUI coordinate fallback input execution backend."""

from app.automation.input.errors import BackendUnavailableError
from app.automation.input.models import MouseButton
from app.logging import logger

try:
    import pyautogui

    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = (
        False  # Controlled by Friday's InputFailsafe to prevent conflicts
    )
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False


class PyAutoGUIInputBackend:
    """PyAutoGUI fallback execution backend for coordinate-based automation."""

    def __init__(self) -> None:
        self._held_modifiers: set[str] = set()
        self._held_buttons: set[MouseButton] = set()

    def is_available(self) -> bool:
        """Check if PyAutoGUI backend is available."""
        return PYAUTOGUI_AVAILABLE

    def move_to(self, x: int, y: int, duration: float = 0.0) -> None:
        """Move cursor using PyAutoGUI."""
        if not self.is_available():
            raise BackendUnavailableError("PyAutoGUI backend unavailable.")
        try:
            pyautogui.moveTo(x=int(x), y=int(y), duration=float(duration))
        except Exception as exc:
            logger.error(f"PyAutoGUI move_to failed: {exc}")

    def click(
        self,
        x: int,
        y: int,
        button: MouseButton = MouseButton.LEFT,
        click_count: int = 1,
    ) -> None:
        """Execute mouse click using PyAutoGUI."""
        if not self.is_available():
            raise BackendUnavailableError("PyAutoGUI backend unavailable.")
        btn_str = button.value.lower()
        try:
            pyautogui.click(x=int(x), y=int(y), clicks=int(click_count), button=btn_str)
        except Exception as exc:
            logger.error(f"PyAutoGUI click failed: {exc}")

    def mouse_down(
        self, x: int, y: int, button: MouseButton = MouseButton.LEFT
    ) -> None:
        """Mouse down using PyAutoGUI."""
        if not self.is_available():
            raise BackendUnavailableError("PyAutoGUI backend unavailable.")
        btn_str = button.value.lower()
        pyautogui.mouseDown(x=int(x), y=int(y), button=btn_str)
        self._held_buttons.add(button)

    def mouse_up(self, x: int, y: int, button: MouseButton = MouseButton.LEFT) -> None:
        """Mouse up using PyAutoGUI."""
        if not self.is_available():
            raise BackendUnavailableError("PyAutoGUI backend unavailable.")
        btn_str = button.value.lower()
        pyautogui.mouseUp(x=int(x), y=int(y), button=btn_str)
        self._held_buttons.discard(button)

    def key_down(self, key_name: str) -> None:
        """Key down using PyAutoGUI."""
        if not self.is_available():
            raise BackendUnavailableError("PyAutoGUI backend unavailable.")
        key_clean = key_name.lower()
        pyautogui.keyDown(key_clean)
        self._held_modifiers.add(key_clean)

    def key_up(self, key_name: str) -> None:
        """Key up using PyAutoGUI."""
        if not self.is_available():
            raise BackendUnavailableError("PyAutoGUI backend unavailable.")
        key_clean = key_name.lower()
        pyautogui.keyUp(key_clean)
        self._held_modifiers.discard(key_clean)

    def press_key(self, key_name: str) -> None:
        """Press key using PyAutoGUI."""
        if not self.is_available():
            raise BackendUnavailableError("PyAutoGUI backend unavailable.")
        pyautogui.press(key_name.lower())

    def press_hotkey(self, keys: list[str]) -> None:
        """Press hotkey combination using PyAutoGUI with modifier cleanup."""
        if not self.is_available() or not keys:
            return
        keys_clean = [k.lower() for k in keys]
        try:
            pyautogui.hotkey(*keys_clean)
        finally:
            for k in keys_clean:
                try:
                    pyautogui.keyUp(k)
                except Exception:
                    pass

    def type_text(self, text: str, interval_sec: float = 0.05) -> None:
        """Type text using PyAutoGUI."""
        if not self.is_available() or not text:
            return
        pyautogui.write(text, interval=interval_sec)

    def release_all_inputs(self) -> None:
        """Release all held PyAutoGUI inputs."""
        if not self.is_available():
            return
        for btn in list(self._held_buttons) or [
            MouseButton.LEFT,
            MouseButton.RIGHT,
            MouseButton.MIDDLE,
        ]:
            try:
                pyautogui.mouseUp(button=btn.value.lower())
            except Exception:
                pass
        self._held_buttons.clear()

        for k in list(self._held_modifiers) or ["ctrl", "alt", "shift", "win"]:
            try:
                pyautogui.keyUp(k)
            except Exception:
                pass
        self._held_modifiers.clear()
