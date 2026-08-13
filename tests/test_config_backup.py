"""Unit tests for ConfigBackupManager."""

from pathlib import Path

from app.config.backup_manager import ConfigBackupManager
from app.utilities.file_utils import read_json_file, write_json_file


def test_config_backup_creation_and_restore(tmp_path: Path):
    backup_dir = tmp_path / "backups"
    cbm = ConfigBackupManager(backup_dir=backup_dir)

    settings_file = tmp_path / "settings.json"
    data = {"version": "1.0", "test_key": "initial_val"}
    write_json_file(settings_file, data)

    backup_file = cbm.create_backup(settings_file=settings_file)
    assert backup_file.exists()
    assert len(cbm.list_backups()) == 1

    # Modify settings file
    write_json_file(settings_file, {"version": "1.0", "test_key": "modified_val"})

    # Restore backup
    restored = cbm.restore_backup(backup_file=backup_file, target_file=settings_file)
    assert restored is True
    restored_data = read_json_file(settings_file)
    assert restored_data["test_key"] == "initial_val"
