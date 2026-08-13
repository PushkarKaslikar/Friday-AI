"""Futuristic AI OS visual identity color tokens for Dark and Light themes."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ColorPalette:
    """Futuristic AI Operating System color palette definitions."""

    bg_primary: str
    bg_secondary: str
    bg_card: str
    bg_hover: str
    bg_selected: str

    accent: str
    accent_hover: str
    accent_light: str
    accent_cyan: str

    text_primary: str
    text_secondary: str
    text_muted: str
    text_on_accent: str

    border: str
    border_light: str
    border_glow: str

    status_success: str
    status_warning: str
    status_error: str
    status_info: str


DARK_PALETTE: Final[ColorPalette] = ColorPalette(
    bg_primary="#000000",
    bg_secondary="#090A0F",
    bg_card="#11131C",
    bg_hover="#181A26",
    bg_selected="#222638",
    accent="#00F0FF",
    accent_hover="#00C4D4",
    accent_light="rgba(0, 240, 255, 0.12)",
    accent_cyan="#00F0FF",
    text_primary="#F8FAFC",
    text_secondary="#94A3B8",
    text_muted="#64748B",
    text_on_accent="#000000",
    border="#1F2438",
    border_light="#2E3550",
    border_glow="rgba(0, 240, 255, 0.3)",
    status_success="#10B981",
    status_warning="#F59E0B",
    status_error="#EF4444",
    status_info="#3B82F6",
)

LIGHT_PALETTE: Final[ColorPalette] = ColorPalette(
    bg_primary="#F8FAFC",
    bg_secondary="#F1F5F9",
    bg_card="#FFFFFF",
    bg_hover="#E2E8F0",
    bg_selected="#CBD5E1",
    accent="#0284C7",
    accent_hover="#0369A1",
    accent_light="rgba(2, 132, 199, 0.12)",
    accent_cyan="#0284C7",
    text_primary="#0F172A",
    text_secondary="#475569",
    text_muted="#94A3B8",
    text_on_accent="#FFFFFF",
    border="#E2E8F0",
    border_light="#CBD5E1",
    border_glow="rgba(2, 132, 199, 0.2)",
    status_success="#059669",
    status_warning="#D97706",
    status_error="#DC2626",
    status_info="#2563EB",
)
