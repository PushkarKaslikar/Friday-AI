"""Configuration Migrator for upgrading schema versions seamlessly."""

from typing import Any

from app.logging import logger

CURRENT_SCHEMA_VERSION = "1.0"


class ConfigMigrator:
    """Handles migration of settings dictionaries between schema versions."""

    def migrate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Migrate raw configuration dictionary to current schema version.

        Args:
            data: Raw dictionary loaded from configuration file.

        Returns:
            dict: Upgraded configuration dictionary.
        """
        version = str(data.get("version", "1.0"))
        if version == CURRENT_SCHEMA_VERSION:
            return data

        logger.info(
            f"ConfigMigrator: Migrating configuration from v{version} to v{CURRENT_SCHEMA_VERSION}..."
        )

        # Placeholders for future schema migrations
        data["version"] = CURRENT_SCHEMA_VERSION
        return data
