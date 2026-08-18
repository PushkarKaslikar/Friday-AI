"""Semantic Element Finder implementation using structured criteria and match modes."""

from typing import Any

from app.automation.models import (
    AutomationElement,
    ElementSearchResult,
    ElementSearchStatus,
    MatchMode,
    normalize_control_type,
)
from app.automation.uia.element_finder_interface import IElementFinder
from app.automation.uia.tree_walker import UITreeWalker
from app.logging import logger


class ElementFinder(IElementFinder):
    """Locates UI elements semantically without requiring pywinauto query syntax."""

    def __init__(
        self,
        tree_walker: UITreeWalker | None = None,
        default_match_mode: MatchMode = MatchMode.EXACT,
    ) -> None:
        self.tree_walker = tree_walker or UITreeWalker()
        self.default_match_mode = default_match_mode

    def _match_string(self, source: str, target: str, mode: MatchMode) -> bool:
        """Perform string matching according to MatchMode."""
        if not target:
            return True
        if not source:
            return False

        if mode == MatchMode.EXACT:
            return source == target
        elif mode == MatchMode.CASE_INSENSITIVE:
            return source.lower() == target.lower()
        elif mode == MatchMode.CONTAINS:
            return target.lower() in source.lower()
        elif mode == MatchMode.STARTS_WITH:
            return source.lower().startswith(target.lower())
        return target.lower() in source.lower()

    def _matches_criteria(
        self,
        element: AutomationElement,
        criteria: dict[str, Any],
        match_mode: MatchMode,
    ) -> bool:
        """Evaluate if an AutomationElement satisfies combined selector criteria."""
        for key, expected in criteria.items():
            if expected is None:
                continue

            key_lower = key.lower()

            if key_lower == "name":
                if not self._match_string(element.name, str(expected), match_mode):
                    return False
            elif key_lower in ("automation_id", "automationid"):
                if not self._match_string(
                    element.automation_id, str(expected), match_mode
                ):
                    return False
            elif key_lower in ("control_type", "controltype"):
                expected_norm = normalize_control_type(str(expected))
                if element.control_type.lower() != expected_norm.lower():
                    return False
            elif key_lower in ("class_name", "classname"):
                if not self._match_string(
                    element.class_name, str(expected), match_mode
                ):
                    return False
            elif key_lower in ("process_id", "pid"):
                if element.process_id != int(expected):
                    return False
            elif key_lower in ("window_handle", "hwnd"):
                if element.window_handle != int(expected):
                    return False
            elif key_lower in ("is_enabled", "enabled"):
                if element.is_enabled != bool(expected):
                    return False
            elif key_lower in ("is_visible", "visible"):
                if element.is_visible != bool(expected):
                    return False

        return True

    def _collect_descendants(
        self,
        raw_node: Any,
        domain_node: AutomationElement,
        criteria: dict[str, Any],
        match_mode: MatchMode,
        matched: list[AutomationElement],
        visited: set[str],
        max_nodes: int = 500,
        max_depth: int = 10,
    ) -> bool:
        """Recursively collect descendant elements matching criteria."""
        if len(matched) >= max_nodes or domain_node.depth >= max_depth:
            return True

        sig = f"{domain_node.native_window_handle}_{domain_node.automation_id}_{domain_node.name}_{domain_node.control_type}_{domain_node.depth}"
        if sig in visited:
            return False
        visited.add(sig)

        if self._matches_criteria(domain_node, criteria, match_mode):
            matched.append(domain_node)

        children_tuples = self.tree_walker.get_children(raw_node, domain_node)
        truncated = False
        for child_raw, child_domain in children_tuples:
            tr = self._collect_descendants(
                child_raw,
                child_domain,
                criteria,
                match_mode,
                matched,
                visited,
                max_nodes=max_nodes,
                max_depth=max_depth,
            )
            if tr:
                truncated = True
                break

        return truncated

    def find_by_properties(
        self,
        criteria: dict[str, Any],
        match_mode: MatchMode = MatchMode.EXACT,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
    ) -> ElementSearchResult:
        """Find all elements matching combined structured criteria dictionary."""
        if not criteria:
            return ElementSearchResult(
                status=ElementSearchStatus.ERROR,
                matched_elements=[],
                match_count=0,
                query=criteria,
                diagnostics={"error": "Empty search criteria provided."},
            )

        if raw_root is None or root_element is None:
            return ElementSearchResult(
                status=ElementSearchStatus.NOT_FOUND,
                matched_elements=[],
                match_count=0,
                query=criteria,
                diagnostics={"reason": "No root element provided for search scope."},
            )

        matched: list[AutomationElement] = []
        visited: set[str] = set()

        truncated = self._collect_descendants(
            raw_root,
            root_element,
            criteria,
            match_mode,
            matched,
            visited,
            max_nodes=self.tree_walker.max_nodes,
            max_depth=self.tree_walker.max_depth,
        )

        match_count = len(matched)
        if match_count == 0:
            status = ElementSearchStatus.NOT_FOUND
        elif match_count == 1:
            status = ElementSearchStatus.FOUND
        else:
            status = ElementSearchStatus.AMBIGUOUS

        if truncated and status != ElementSearchStatus.NOT_FOUND:
            status = ElementSearchStatus.LIMIT_REACHED

        return ElementSearchResult(
            status=status,
            matched_elements=matched,
            match_count=match_count,
            query=criteria,
            truncated=truncated,
            diagnostics={
                "search_mode": (
                    match_mode.value
                    if isinstance(match_mode, MatchMode)
                    else match_mode
                ),
                "nodes_inspected": len(visited),
            },
        )

    def find_by_name(
        self,
        name: str,
        match_mode: MatchMode = MatchMode.EXACT,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
    ) -> ElementSearchResult:
        """Find element by name property."""
        return self.find_by_properties(
            {"name": name},
            match_mode=match_mode,
            raw_root=raw_root,
            root_element=root_element,
        )

    def find_by_automation_id(
        self,
        automation_id: str,
        match_mode: MatchMode = MatchMode.EXACT,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
    ) -> ElementSearchResult:
        """Find element by automation_id property."""
        return self.find_by_properties(
            {"automation_id": automation_id},
            match_mode=match_mode,
            raw_root=raw_root,
            root_element=root_element,
        )

    def find_by_control_type(
        self,
        control_type: str,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
    ) -> ElementSearchResult:
        """Find elements matching control type."""
        return self.find_by_properties(
            {"control_type": control_type},
            match_mode=MatchMode.EXACT,
            raw_root=raw_root,
            root_element=root_element,
        )

    def find_descendant(
        self,
        criteria: dict[str, Any],
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
        match_mode: MatchMode = MatchMode.EXACT,
    ) -> ElementSearchResult:
        """Find unique matching descendant element."""
        res = self.find_by_properties(
            criteria,
            match_mode=match_mode,
            raw_root=raw_root,
            root_element=root_element,
        )
        if res.status == ElementSearchStatus.AMBIGUOUS:
            logger.warning(
                f"Ambiguous descendant match for criteria {criteria}: found {res.match_count} candidates."
            )
        return res

    def find_children(
        self,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
        criteria: dict[str, Any] | None = None,
    ) -> ElementSearchResult:
        """Find direct child elements matching optional criteria."""
        if raw_root is None or root_element is None:
            return ElementSearchResult(
                status=ElementSearchStatus.NOT_FOUND,
                matched_elements=[],
                match_count=0,
                query=criteria or {},
            )

        children_tuples = self.tree_walker.get_children(raw_root, root_element)
        matched: list[AutomationElement] = []

        for _, child_domain in children_tuples:
            if criteria:
                if self._matches_criteria(
                    child_domain, criteria, self.default_match_mode
                ):
                    matched.append(child_domain)
            else:
                matched.append(child_domain)

        match_count = len(matched)
        status = (
            ElementSearchStatus.FOUND
            if match_count == 1
            else (
                ElementSearchStatus.AMBIGUOUS
                if match_count > 1
                else ElementSearchStatus.NOT_FOUND
            )
        )

        return ElementSearchResult(
            status=status,
            matched_elements=matched,
            match_count=match_count,
            query=criteria or {},
        )
