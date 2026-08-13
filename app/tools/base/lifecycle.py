"""Tool lifecycle state enum."""

from enum import Enum


class ToolState(str, Enum):
    """Tool lifecycle state machine enum."""

    DISCOVERED = "DISCOVERED"
    REGISTERED = "REGISTERED"
    INITIALIZED = "INITIALIZED"
    READY = "READY"
    DISABLED = "DISABLED"
    FAILED = "FAILED"
    SHUTDOWN = "SHUTDOWN"
