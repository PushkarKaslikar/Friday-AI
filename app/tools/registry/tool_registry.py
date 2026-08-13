"""Centralized thread-safe Tool Registry for tool registration and lifecycle management."""

import threading
from typing import Optional

from app.logging import logger
from app.services.events.event_bus import EventBus
from app.tools.base.metadata import ToolMetadata
from app.tools.base.tool import BaseTool
from app.tools.events.tool_events import ToolDisabled, ToolEnabled, ToolRegistered


class ToolRegistry:
    """Centralized thread-safe registry managing tool instances, metadata, and status toggles."""

    _instance: Optional["ToolRegistry"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, event_bus: EventBus | None = None) -> None:
        if getattr(self, "_initialized", False):
            return

        self.event_bus = event_bus or EventBus()
        self._lock = threading.RLock()
        self._tools: dict[str, BaseTool] = {}
        self._initialized = True
        logger.info("ToolRegistry initialized.")

    def register_tool(self, tool: BaseTool) -> bool:
        """Register a tool instance in the registry.

        Args:
            tool: BaseTool instance.

        Returns:
            bool: True if registration succeeded.
        """
        if not isinstance(tool, BaseTool):
            logger.error("ToolRegistry: Object must inherit from BaseTool.")
            return False

        tool_id = tool.tool_id
        with self._lock:
            if tool_id in self._tools:
                logger.warning(
                    f"ToolRegistry: Tool '{tool_id}' is already registered. Overwriting."
                )

            self._tools[tool_id] = tool
            logger.info(
                f"ToolRegistry: Registered tool '{tool_id}' ({tool.metadata.display_name})."
            )

        self.event_bus.publish(
            ToolRegistered(
                tool_id=tool_id,
                name=tool.metadata.name,
                category=tool.metadata.category.value,
            )
        )
        return True

    def unregister_tool(self, tool_id: str) -> bool:
        """Unregister a tool by tool_id."""
        with self._lock:
            tool = self._tools.pop(tool_id, None)
            if tool:
                logger.info(f"ToolRegistry: Unregistered tool '{tool_id}'.")
                return True
        return False

    def get_tool(self, tool_id: str) -> BaseTool | None:
        """Retrieve registered tool instance by tool_id."""
        with self._lock:
            return self._tools.get(tool_id)

    def has_tool(self, tool_id: str) -> bool:
        """Check if tool_id exists in registry."""
        with self._lock:
            return tool_id in self._tools

    def enable_tool(self, tool_id: str) -> bool:
        """Enable a registered tool."""
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool:
                tool.metadata.is_enabled = True
                logger.info(f"ToolRegistry: Enabled tool '{tool_id}'.")
                self.event_bus.publish(ToolEnabled(tool_id=tool_id))
                return True
        return False

    def disable_tool(self, tool_id: str) -> bool:
        """Disable a registered tool."""
        with self._lock:
            tool = self._tools.get(tool_id)
            if tool:
                tool.metadata.is_enabled = False
                logger.info(f"ToolRegistry: Disabled tool '{tool_id}'.")
                self.event_bus.publish(ToolDisabled(tool_id=tool_id))
                return True
        return False

    def list_tools(self) -> list[ToolMetadata]:
        """Get copy of all registered tool metadata models."""
        with self._lock:
            return [tool.metadata for tool in self._tools.values()]

    def list_tool_instances(self) -> list[BaseTool]:
        """Get list of all active tool instances."""
        with self._lock:
            return list(self._tools.values())

    @property
    def registered_count(self) -> int:
        """Get count of registered tools."""
        with self._lock:
            return len(self._tools)

    def clear(self) -> None:
        """Clear all registered tools."""
        with self._lock:
            self._tools.clear()
