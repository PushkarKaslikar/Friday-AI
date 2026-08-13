"""Installer Architecture specifications for Inno Setup or WiX deployment packaging."""

from dataclasses import dataclass, field
from typing import Final

from app.platform.identity.app_identity import APP_IDENTITY


@dataclass(frozen=True)
class InstallerConfig:
    """Installer configuration manifest specification."""

    app_name: str = APP_IDENTITY.name
    app_version: str = APP_IDENTITY.version
    publisher: str = APP_IDENTITY.company
    support_url: str = APP_IDENTITY.website
    default_install_dir: str = r"{autopf}\Friday AI"
    output_installer_name: str = f"FridayAI_Setup_v{APP_IDENTITY.version}.exe"

    create_desktop_shortcut: bool = True
    create_start_menu_shortcut: bool = True
    create_startup_entry: bool = True

    shortcut_name: str = "Friday AI Assistant"
    executable_name: str = "Friday.exe"
    uninstall_registry_key: str = (
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FridayAI"
    )

    custom_messages: list[str] = field(
        default_factory=lambda: [
            "Installing Friday AI Assistant...",
            "Registering Windows Startup shortcut...",
            "Configuring Windows Desktop shortcuts...",
        ]
    )


INSTALLER_MANIFEST: Final[InstallerConfig] = InstallerConfig()
