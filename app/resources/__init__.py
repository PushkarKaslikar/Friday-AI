"""Resources package for asset management and file resolution."""

from pathlib import Path

from app.constants.paths import ASSETS_DIR


class ResourceManager:
    """Manages access to static assets (icons, images, stylesheets)."""

    def __init__(self, assets_dir: Path | None = None) -> None:
        self.assets_dir = assets_dir or ASSETS_DIR

    def get_asset_path(self, relative_path: str) -> Path:
        """Resolve absolute path to asset file inside assets directory."""
        return (self.assets_dir / relative_path).resolve()


__all__ = ["ResourceManager"]
