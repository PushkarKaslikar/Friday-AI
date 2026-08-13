"""Tool Discovery Service querying registered tools by category, risk, permissions, and tags."""

from app.tools.base.metadata import ToolMetadata
from app.tools.base.permissions import ToolPermission
from app.tools.base.risk import ToolRiskLevel
from app.tools.categories import ToolCategory
from app.tools.registry.tool_registry import ToolRegistry


class ToolDiscoveryService:
    """Service supporting query filtering and text search across ToolRegistry tools."""

    def __init__(self, registry: ToolRegistry | None = None) -> None:
        self.registry = registry or ToolRegistry()

    def get_tool(self, tool_id: str) -> ToolMetadata | None:
        """Find tool metadata by tool_id."""
        tool = self.registry.get_tool(tool_id)
        return tool.metadata if tool else None

    def find_by_category(self, category: ToolCategory) -> list[ToolMetadata]:
        """Find all registered tools in a specific category."""
        return [
            meta for meta in self.registry.list_tools() if meta.category == category
        ]

    def find_by_permission(self, permission: ToolPermission) -> list[ToolMetadata]:
        """Find tools requiring a specific permission capability."""
        return [
            meta
            for meta in self.registry.list_tools()
            if permission in meta.permissions
        ]

    def find_by_risk_level(self, risk_level: ToolRiskLevel) -> list[ToolMetadata]:
        """Find tools matching a specified risk level."""
        return [
            meta for meta in self.registry.list_tools() if meta.risk_level == risk_level
        ]

    def find_by_tag(self, tag: str) -> list[ToolMetadata]:
        """Find tools matching a specific search tag."""
        target = tag.lower().strip()
        return [
            meta
            for meta in self.registry.list_tools()
            if any(target == t.lower() for t in meta.tags)
        ]

    def search_tools(self, query: str) -> list[ToolMetadata]:
        """Perform text search across tool_id, name, display_name, description, and tags.

        Args:
            query: Search query string.

        Returns:
            list[ToolMetadata]: Matching metadata models sorted by relevance.
        """
        q = query.lower().strip()
        if not q:
            return self.registry.list_tools()

        results = []
        for meta in self.registry.list_tools():
            match_score = 0
            if q in meta.tool_id.lower():
                match_score += 10
            if q in meta.name.lower():
                match_score += 8
            if q in meta.display_name.lower():
                match_score += 6
            if q in meta.description.lower():
                match_score += 3
            if any(q in t.lower() for t in meta.tags):
                match_score += 4

            if match_score > 0:
                results.append((match_score, meta))

        results.sort(key=lambda item: item[0], reverse=True)
        return [meta for _, meta in results]
