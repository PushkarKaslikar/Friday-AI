"""UI Tree Walker subsystem for safe traversal and dump generation of UI hierarchies."""

from typing import Any

from app.automation.models import (
    AutomationElement,
    AutomationTreeNode,
)
from app.automation.uia.element_adapter import ElementAdapter
from app.logging import logger


class UITreeWalker:
    """Traverses UI hierarchy with depth bounds, node limits, cycle protection, and formatting."""

    def __init__(
        self,
        max_depth: int = 10,
        max_nodes: int = 500,
        max_children_per_node: int = 50,
        include_offscreen: bool = False,
        include_disabled: bool = False,
        sanitize_sensitive: bool = True,
    ) -> None:
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.max_children_per_node = max_children_per_node
        self.include_offscreen = include_offscreen
        self.include_disabled = include_disabled
        self.sanitize_sensitive = sanitize_sensitive

    def get_children(
        self, raw_parent: Any, parent_element: AutomationElement
    ) -> list[tuple[Any, AutomationElement]]:
        """Retrieve direct children of a raw element."""
        results: list[tuple[Any, AutomationElement]] = []
        if raw_parent is None:
            return results

        children_raw = []
        try:
            if hasattr(raw_parent, "children"):
                children_raw = raw_parent.children()
            elif hasattr(raw_parent, "get_children"):
                children_raw = raw_parent.get_children()
            elif hasattr(raw_parent, "element_info") and hasattr(
                raw_parent.element_info, "children"
            ):
                children_raw = raw_parent.element_info.children()
        except Exception as exc:
            logger.debug(
                f"Failed to fetch children of element '{parent_element.name}': {exc}"
            )
            return results

        count = 0
        for child_raw in children_raw:
            if count >= self.max_children_per_node:
                break
            try:
                elem = ElementAdapter.create_automation_element(
                    child_raw,
                    parent_id=parent_element.element_id,
                    depth=parent_element.depth + 1,
                )
                if not self.include_disabled and not elem.is_enabled:
                    continue
                if not self.include_offscreen and elem.is_offscreen:
                    continue
                results.append((child_raw, elem))
                count += 1
            except Exception as exc:
                logger.debug(f"Child conversion error: {exc}")
                continue

        return results

    def traverse_tree(
        self,
        raw_root: Any,
        root_element: AutomationElement,
        max_depth: int | None = None,
        max_nodes: int | None = None,
        control_type_filter: str | None = None,
    ) -> tuple[AutomationTreeNode, bool]:
        """Traverse hierarchy rooted at root_element up to depth/node limits with duplicate protection."""
        limit_depth = max_depth if max_depth is not None else self.max_depth
        limit_nodes = max_nodes if max_nodes is not None else self.max_nodes

        visited_ids: set[str] = set()
        node_count = 0
        truncated = False

        filter_type = control_type_filter.lower() if control_type_filter else None

        def _build_node(
            raw_node: Any, domain_elem: AutomationElement, current_depth: int
        ) -> AutomationTreeNode:
            nonlocal node_count, truncated

            node_count += 1
            snap = ElementAdapter.create_snapshot(domain_elem)
            if self.sanitize_sensitive and snap.is_password:
                snap.value = "[REDACTED]"

            tree_node = AutomationTreeNode(
                element=snap,
                depth=current_depth,
                children=[],
                truncated=False,
            )

            if current_depth >= limit_depth or node_count >= limit_nodes:
                if node_count >= limit_nodes or current_depth >= limit_depth:
                    truncated = True
                tree_node.truncated = True
                return tree_node

            # Unique identity signature for cycle protection
            identity_sig = f"{domain_elem.native_window_handle}_{domain_elem.automation_id}_{domain_elem.name}_{domain_elem.control_type}_{domain_elem.depth}"
            if identity_sig in visited_ids:
                return tree_node
            visited_ids.add(identity_sig)

            children_tuples = self.get_children(raw_node, domain_elem)
            for child_raw, child_domain in children_tuples:
                if node_count >= limit_nodes:
                    truncated = True
                    tree_node.truncated = True
                    break

                if filter_type and child_domain.control_type.lower() != filter_type:
                    # Continue inspecting descendants even if this child doesn't match filter
                    child_node = _build_node(child_raw, child_domain, current_depth + 1)
                    if child_node.children:
                        tree_node.children.extend(child_node.children)
                else:
                    child_node = _build_node(child_raw, child_domain, current_depth + 1)
                    tree_node.children.append(child_node)

            return tree_node

        root_tree = _build_node(raw_root, root_element, current_depth=0)
        return root_tree, truncated

    def dump_tree_string(
        self,
        raw_root: Any,
        root_element: AutomationElement,
        max_depth: int | None = None,
        max_nodes: int | None = None,
        control_type_filter: str | None = None,
    ) -> str:
        """Produce human-readable formatted string tree dump."""
        tree_node, truncated = self.traverse_tree(
            raw_root,
            root_element,
            max_depth=max_depth,
            max_nodes=max_nodes,
            control_type_filter=control_type_filter,
        )

        lines: list[str] = []

        def _format_node(node: AutomationTreeNode, indent_level: int) -> None:
            indent = "  " * indent_level
            el = node.element

            name_str = f" '{el.name}'" if el.name else ""
            auto_id_str = f" [id={el.automation_id}]" if el.automation_id else ""
            val_str = f" value={el.value}" if el.value else ""
            bounds_str = (
                f" [{el.bounding_rectangle['width']}x{el.bounding_rectangle['height']} at ({el.bounding_rectangle['left']},{el.bounding_rectangle['top']})]"
                if el.bounding_rectangle
                else ""
            )

            line = (
                f"{indent}{el.control_type}{name_str}{auto_id_str}{bounds_str}{val_str}"
            )
            if node.truncated:
                line += " [TRUNCATED]"
            lines.append(line)

            for child in node.children:
                _format_node(child, indent_level + 1)

        _format_node(tree_node, 0)
        if truncated:
            lines.append(
                "\n[TREE DUMP TRUNCATED: Traversal limits reached (max depth/nodes exceeded)]"
            )

        return "\n".join(lines)
