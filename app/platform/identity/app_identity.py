"""Centralized Application Identity metadata definitions."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ApplicationMetadata:
    """Centralized metadata specification for Friday AI Assistant."""

    name: str = "Friday AI Assistant"
    version: str = "1.0.0"
    company: str = "Friday AI Team"
    author: str = "Pushkar & Friday Contributors"
    website: str = "https://github.com/Pushkar/FridayAI"
    support_email: str = "support@friday-ai.local"
    copyright: str = "Copyright © 2026 Friday AI Team. All rights reserved."
    build_date: str = "2026-08-07"
    build_number: int = 1050
    environment: str = "production"
    target_platform: str = "Windows 11"


APP_IDENTITY: Final[ApplicationMetadata] = ApplicationMetadata()
