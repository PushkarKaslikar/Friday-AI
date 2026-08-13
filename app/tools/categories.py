"""Tool category classification enum for tools."""

from enum import Enum


class ToolCategory(str, Enum):
    """Categorized domain areas for Friday AI Assistant tools."""

    SYSTEM = "SYSTEM"
    WINDOWS = "WINDOWS"
    FILES = "FILES"
    PROCESS = "PROCESS"
    CLIPBOARD = "CLIPBOARD"
    BROWSER = "BROWSER"
    COMMUNICATION = "COMMUNICATION"
    MEDIA = "MEDIA"
    DEVELOPER = "DEVELOPER"
    UTILITY = "UTILITY"
    PLUGIN = "PLUGIN"
