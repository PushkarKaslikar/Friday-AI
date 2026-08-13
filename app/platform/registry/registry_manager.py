"""Windows Registry Manager encapsulating winreg operations for system integration."""

import winreg
from pathlib import Path
from typing import Any

from app.constants.application import APP_NAME
from app.logging import logger
from app.utilities.file_utils import write_json_file
from app.utilities.path_utils import ensure_directory_exists

DEFAULT_REG_KEY_PATH = r"Software\FridayAIAssistant"
RUN_REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"


class RegistryManager:
    """Centralized Windows Registry Manager providing safe winreg operations and backups."""

    def __init__(self, root_key: int = winreg.HKEY_CURRENT_USER) -> None:
        self.root_key = root_key

    def set_value(
        self,
        sub_key: str,
        value_name: str,
        value: Any,
        value_type: int = winreg.REG_SZ,
    ) -> bool:
        """Write a registry key-value pair under Current User root key.

        Args:
            sub_key: Subkey path string (e.g. 'Software\\FridayAIAssistant').
            value_name: Value identifier name.
            value: Data value to write.
            value_type: winreg registry data type enum.

        Returns:
            bool: True if registry write succeeded.
        """
        try:
            key = winreg.CreateKey(self.root_key, sub_key)
            winreg.SetValueEx(key, value_name, 0, value_type, str(value))
            winreg.CloseKey(key)
            logger.info(f"RegistryManager: Set '{sub_key}\\{value_name}' = {value}.")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"RegistryManager: Failed to write registry key '{sub_key}\\{value_name}': {exc}"
            )
            return False

    def get_value(self, sub_key: str, value_name: str, default: Any = None) -> Any:
        """Read a registry value by subkey and name.

        Args:
            sub_key: Subkey path string.
            value_name: Value identifier name.
            default: Fallback default value if key is not found.

        Returns:
            Any: Value read from registry or default fallback.
        """
        try:
            key = winreg.OpenKey(self.root_key, sub_key, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, value_name)
            winreg.CloseKey(key)
            return val
        except FileNotFoundError:
            return default
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                f"RegistryManager: Error reading registry key '{sub_key}\\{value_name}': {exc}"
            )
            return default

    def delete_value(self, sub_key: str, value_name: str) -> bool:
        """Delete a registry value entry."""
        try:
            key = winreg.OpenKey(self.root_key, sub_key, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, value_name)
            winreg.CloseKey(key)
            logger.info(
                f"RegistryManager: Deleted registry value '{sub_key}\\{value_name}'."
            )
            return True
        except FileNotFoundError:
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"RegistryManager: Failed to delete registry value '{sub_key}\\{value_name}': {exc}"
            )
            return False

    def value_exists(self, sub_key: str, value_name: str) -> bool:
        """Check if a registry value entry exists."""
        return self.get_value(sub_key, value_name) is not None

    def backup_key(self, sub_key: str, backup_file_path: str | Path) -> bool:
        """Export key values to a backup JSON file."""
        target = Path(backup_file_path).resolve()
        ensure_directory_exists(target.parent)

        values = {}
        try:
            key = winreg.OpenKey(self.root_key, sub_key, 0, winreg.KEY_READ)
            idx = 0
            while True:
                try:
                    name, val, reg_type = winreg.EnumValue(key, idx)
                    values[name] = {"value": val, "type": reg_type}
                    idx += 1
                except OSError:
                    break
            winreg.CloseKey(key)

            write_json_file(
                target, {"app": APP_NAME, "sub_key": sub_key, "values": values}
            )
            logger.info(
                f"RegistryManager: Backed up key '{sub_key}' to '{target.name}'."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(f"RegistryManager: Backup failed for '{sub_key}': {exc}")
            return False
