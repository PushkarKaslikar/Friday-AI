"""Version Manager handling semantic version parsing, release channels, and build metadata."""

from typing import Any, NamedTuple

from app.platform.identity.app_identity import APP_IDENTITY


class SemanticVersion(NamedTuple):
    major: int
    minor: int
    patch: int
    prerelease: str = ""


class VersionManager:
    """Manages semantic version comparison, build metadata queries, and release channels."""

    def __init__(self, raw_version: str = APP_IDENTITY.version) -> None:
        self.raw_version = raw_version
        self.semver = self.parse_version(raw_version)

    @staticmethod
    def parse_version(version_str: str) -> SemanticVersion:
        """Parse semantic version string into major.minor.patch tuple."""
        clean = version_str.lstrip("v").strip()
        parts = clean.split("-", 1)
        version_numbers = parts[0].split(".")

        major = (
            int(version_numbers[0])
            if len(version_numbers) > 0 and version_numbers[0].isdigit()
            else 1
        )
        minor = (
            int(version_numbers[1])
            if len(version_numbers) > 1 and version_numbers[1].isdigit()
            else 0
        )
        patch = (
            int(version_numbers[2])
            if len(version_numbers) > 2 and version_numbers[2].isdigit()
            else 0
        )
        prerelease = parts[1] if len(parts) > 1 else ""

        return SemanticVersion(
            major=major, minor=minor, patch=patch, prerelease=prerelease
        )

    def get_build_info(self) -> dict[str, Any]:
        """Get summary build information dictionary."""
        return {
            "app_name": APP_IDENTITY.name,
            "version": self.raw_version,
            "build_number": APP_IDENTITY.build_number,
            "build_date": APP_IDENTITY.build_date,
            "environment": APP_IDENTITY.environment,
            "channel": "stable" if not self.semver.prerelease else "beta",
        }
