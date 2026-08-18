"""Interface declaration for semantic UI element finder."""

from abc import ABC, abstractmethod
from typing import Any

from app.automation.models import AutomationElement, ElementSearchResult, MatchMode


class IElementFinder(ABC):
    """Abstract interface for locating UI elements semantically using structured criteria."""

    @abstractmethod
    def find_by_name(
        self,
        name: str,
        match_mode: MatchMode = MatchMode.EXACT,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
    ) -> ElementSearchResult:
        """Find element by accessible name."""

    @abstractmethod
    def find_by_automation_id(
        self,
        automation_id: str,
        match_mode: MatchMode = MatchMode.EXACT,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
    ) -> ElementSearchResult:
        """Find element by UIA AutomationId."""

    @abstractmethod
    def find_by_control_type(
        self,
        control_type: str,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
    ) -> ElementSearchResult:
        """Find elements matching normalized control type."""

    @abstractmethod
    def find_by_properties(
        self,
        criteria: dict[str, Any],
        match_mode: MatchMode = MatchMode.EXACT,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
    ) -> ElementSearchResult:
        """Find elements matching combined structured criteria dictionary."""

    @abstractmethod
    def find_descendant(
        self,
        criteria: dict[str, Any],
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
        match_mode: MatchMode = MatchMode.EXACT,
    ) -> ElementSearchResult:
        """Find unique matching descendant element."""

    @abstractmethod
    def find_children(
        self,
        raw_root: Any = None,
        root_element: AutomationElement | None = None,
        criteria: dict[str, Any] | None = None,
    ) -> ElementSearchResult:
        """Find direct child elements matching optional criteria."""
