"""Configuration Backup Manager managing automatic settings backups and restoration."""

import datetime
from pathlib import Path

from app.constants.paths import CONFIG_DIR, SETTINGS_FILE
from app.logging import logger
from app.utilities.file_utils import read_json_file, write_json_file
from app.utilities.path_utils import ensure_directory_exists

BACKUP_DIR = CONFIG_DIR / "backups"


class ConfigBackupManager:
    """Manages creation, listing, validation, and restoration of configuration backup files."""

    def __init__(self, backup_dir: str | Path | None = None) -> None:
        self.backup_dir = ensure_directory_exists(backup_dir or BACKUP_DIR)

    def create_backup(self, settings_file: str | Path | None = None) -> Path:
        """Create a timestamped backup copy of current settings.json.

        Args:
            settings_file: Path to settings JSON file.

        Returns:
            Path: Path to newly created backup file.
        """
        source_file = Path(settings_file or SETTINGS_FILE).resolve()
        if not source_file.exists():
            now_str = str(datetime.datetime.now())  # noqa: DTZ005
            data = {"version": "1.0", "created_at": now_str}
            write_json_file(source_file, data)

        data = read_json_file(source_file)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")  # noqa: DTZ005
        backup_file = self.backup_dir / f"settings_backup_{timestamp}.json"

        write_json_file(backup_file, data)
        logger.info(
            f"ConfigBackupManager: Created configuration backup at '{backup_file.name}'."
        )
        return backup_file

    def list_backups(self) -> list[Path]:
        """List all available configuration backup files sorted by creation date descending."""
        if not self.backup_dir.exists():
            return []
        backups = sorted(self.backup_dir.glob("settings_backup_*.json"), reverse=True)
        return list(backups)

    def restore_backup(
        self, backup_file: str | Path, target_file: str | Path | None = None
    ) -> bool:
        """Restore settings from a specified backup file.

        Args:
            backup_file: Path to backup JSON file.
            target_file: Path to target settings.json.

        Returns:
            bool: True if restoration completed successfully.
        """
        src = Path(backup_file).resolve()
        target = Path(target_file or SETTINGS_FILE).resolve()

        if not src.exists():
            logger.error(f"ConfigBackupManager: Backup file '{src}' does not exist.")
            return False

        try:
            data = read_json_file(src)
            write_json_file(target, data)
            logger.info(
                f"ConfigBackupManager: Restored configuration from '{src.name}'."
            )
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error(
                f"ConfigBackupManager: Failed to restore backup '{src.name}': {exc}"
            )
            return False
