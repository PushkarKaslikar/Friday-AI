"""Deterministic schema generator and cacheable ToolDefinition registry.

Phase 4.3 - Tool Calling & Function Binding Engine
"""

import threading
from typing import Any

from app.ai.tool_calling.models import ToolDefinition
from app.logging import logger
from app.tools.base.metadata import ToolMetadata
from app.tools.base.tool import BaseTool
from app.tools.registry.tool_registry import ToolRegistry


class ToolSchemaRegistry:
    """Generates canonical ToolDefinition JSON schemas from Phase 2 tools with thread-safe caching."""

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self.tool_registry = tool_registry or ToolRegistry()
        self._lock = threading.RLock()
        self._schema_cache: dict[str, ToolDefinition] = {}

    def get_tool_definition(self, tool_id: str) -> ToolDefinition | None:
        """Get canonical ToolDefinition for a registered tool."""
        with self._lock:
            if tool_id in self._schema_cache:
                return self._schema_cache[tool_id]

            tool = self.tool_registry.get_tool(tool_id)
            if not tool:
                return None

            definition = self._generate_tool_definition(tool)
            self._schema_cache[tool_id] = definition
            return definition

    def generate_all_definitions(
        self, enabled_only: bool = True
    ) -> list[ToolDefinition]:
        """Generate canonical ToolDefinition list for all registered tools."""
        definitions: list[ToolDefinition] = []
        tools = self.tool_registry.list_tool_instances()

        with self._lock:
            for tool in tools:
                if enabled_only and not tool.metadata.is_enabled:
                    continue

                tool_id = tool.tool_id
                if tool_id in self._schema_cache:
                    definitions.append(self._schema_cache[tool_id])
                else:
                    defn = self._generate_tool_definition(tool)
                    self._schema_cache[tool_id] = defn
                    definitions.append(defn)

        return definitions

    def _generate_tool_definition(self, tool: BaseTool) -> ToolDefinition:
        """Extract metadata and convert Pydantic input_schema to canonical ToolDefinition."""
        meta: ToolMetadata = tool.metadata
        params_schema: dict[str, Any] = {}
        req_params: list[str] = []

        if meta.input_schema:
            try:
                json_schema = meta.input_schema.model_json_schema()
                properties = json_schema.get("properties", {})
                req_params = json_schema.get("required", [])

                for prop_name, prop_data in properties.items():
                    params_schema[prop_name] = {
                        "type": prop_data.get("type", "string"),
                        "description": prop_data.get("description", ""),
                    }
                    if "enum" in prop_data:
                        params_schema[prop_name]["enum"] = prop_data["enum"]
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"ToolSchemaRegistry: Failed to parse input_schema for tool '{meta.tool_id}': {exc}"
                )

        return ToolDefinition(
            tool_name=meta.tool_id,
            description=meta.description,
            category=(
                meta.category.value
                if hasattr(meta.category, "value")
                else str(meta.category)
            ),
            parameters_schema=params_schema,
            required_parameters=req_params,
            risk_level=(
                meta.risk_level.value
                if hasattr(meta.risk_level, "value")
                else str(meta.risk_level)
            ),
            permissions=[
                p.value if hasattr(p, "value") else str(p) for p in meta.permissions
            ],
            confirmation_required=meta.confirmation_required,
            is_enabled=meta.is_enabled,
            version=meta.version,
        )

    def invalidate_cache(self, tool_id: str | None = None) -> None:
        """Clear cache for specific tool_id or purge entire cache."""
        with self._lock:
            if tool_id:
                self._schema_cache.pop(tool_id, None)
                logger.debug(
                    f"ToolSchemaRegistry: Cache invalidated for tool '{tool_id}'."
                )
            else:
                self._schema_cache.clear()
                logger.debug("ToolSchemaRegistry: Entire schema cache invalidated.")
