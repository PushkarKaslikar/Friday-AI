"""Tool risk classification enum."""

from enum import Enum


class ToolRiskLevel(str, Enum):
    """Tool risk rating levels for security evaluation."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
