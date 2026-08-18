"""Interface definition for the UI Automation Engine."""

from abc import ABC, abstractmethod
from typing import Any

from app.automation.models import AutomationElement, WindowSearchResult
from app.automation.uia.element_finder_interface import IElementFinder
from app.automation.uia.tree_walker import UITreeWalker


class IUIAutomationEngine(ABC):
    """Abstract interface for top-level Windows UI Automation operations."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if UIA engine backend is available on host OS."""

    @abstractmethod
    def initialize() -> bool:
        """Initialize UIA backend safely."""

    @abstractmethod
    def get_health_status(self) -> dict[str, Any]:
        """Get structured subsystem health report."""

    @abstractmethod
    def resolve_window(
        self,
        title: str | None = None,
        process_id: int | None = None,
        process_name: str | None = None,
        hwnd: int | None = None,
    ) -> WindowSearchResult:
        """Resolve top-level application window by criteria."""

    @abstractmethod
    def get_root_element(self, hwnd: int) -> tuple[Any, AutomationElement]:
        """Get top-level root element wrapper for specified window handle."""

    @abstractmethod
    def get_tree_walker(self) -> UITreeWalker:
        """Get tree walker instance."""

    @abstractmethod
    def get_element_finder(self) -> IElementFinder:
        """Get element finder instance."""

    @abstractmethod
    def invoke_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely execute InvokePattern on element."""

    @abstractmethod
    def get_element_value(
        self, raw_element: Any, element: AutomationElement
    ) -> str | None:
        """Safely read value from element via ValuePattern."""

    @abstractmethod
    def set_element_value(
        self, raw_element: Any, element: AutomationElement, value: str
    ) -> bool:
        """Safely set value on element via ValuePattern."""

    @abstractmethod
    def toggle_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely toggle element state via TogglePattern."""

    @abstractmethod
    def select_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely select item via SelectionItemPattern."""

    @abstractmethod
    def expand_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely expand element via ExpandCollapsePattern."""

    @abstractmethod
    def collapse_element(self, raw_element: Any, element: AutomationElement) -> bool:
        """Safely collapse element via ExpandCollapsePattern."""
