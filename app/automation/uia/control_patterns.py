"""Control Pattern abstraction layer for safe low-level UIA operations."""

from typing import Any

from app.automation.errors import (
    ElementInvalidError,
    ElementStaleError,
    PatternNotSupportedError,
)
from app.automation.models import AutomationElement
from app.logging import logger


class ControlPatternManager:
    """Manages UIA control pattern discovery and safe execution of low-level UIA pattern actions."""

    @staticmethod
    def validate_element_action(
        raw_element: Any, element: AutomationElement, required_pattern: str
    ) -> None:
        """Validate element state and pattern support before executing an action."""
        if raw_element is None or element is None:
            raise ElementInvalidError("Element reference is None.")

        if not element.is_enabled:
            raise ElementInvalidError(
                f"Element '{element.name}' ({element.control_type}) is disabled.",
                details={"element_id": element.element_id},
            )

        if required_pattern not in element.supported_patterns:
            raise PatternNotSupportedError(
                f"Element '{element.name}' ({element.control_type}) does not support pattern '{required_pattern}'.",
                details={
                    "element_id": element.element_id,
                    "supported_patterns": element.supported_patterns,
                    "requested_pattern": required_pattern,
                },
            )

    @staticmethod
    def invoke(raw_element: Any, element: AutomationElement) -> bool:
        """Execute InvokePattern.Invoke() on button or clickable element."""
        ControlPatternManager.validate_element_action(
            raw_element, element, "InvokePattern"
        )
        try:
            if hasattr(raw_element, "invoke"):
                raw_element.invoke()
                logger.debug(
                    f"Executed InvokePattern on element '{element.name}' ({element.element_id})"
                )
                return True
            elif hasattr(raw_element, "iface_invoke") and raw_element.iface_invoke:
                raw_element.iface_invoke.Invoke()
                return True
            raise PatternNotSupportedError("Raw element missing invoke implementation.")
        except Exception as exc:
            logger.error(f"InvokePattern failed on element '{element.name}': {exc}")
            raise ElementStaleError(
                f"Failed to invoke element '{element.name}'", cause=exc
            )

    @staticmethod
    def get_value(raw_element: Any, element: AutomationElement) -> str | None:
        """Retrieve value via ValuePattern."""
        ControlPatternManager.validate_element_action(
            raw_element, element, "ValuePattern"
        )
        if element.is_password:
            return "[REDACTED]"
        try:
            if hasattr(raw_element, "iface_value") and raw_element.iface_value:
                return str(raw_element.iface_value.CurrentValue)
            elif hasattr(raw_element, "window_text"):
                return str(raw_element.window_text())
            return element.value
        except Exception as exc:
            raise ElementStaleError(
                f"Failed to get value from element '{element.name}'", cause=exc
            )

    @staticmethod
    def set_value(raw_element: Any, element: AutomationElement, value: str) -> bool:
        """Set control text via ValuePattern."""
        ControlPatternManager.validate_element_action(
            raw_element, element, "ValuePattern"
        )
        try:
            if hasattr(raw_element, "set_edit_text"):
                raw_element.set_edit_text(value)
                return True
            elif hasattr(raw_element, "iface_value") and raw_element.iface_value:
                raw_element.iface_value.SetValue(value)
                return True
            raise PatternNotSupportedError(
                "Raw element missing set_value implementation."
            )
        except Exception as exc:
            raise ElementStaleError(
                f"Failed to set value on element '{element.name}'", cause=exc
            )

    @staticmethod
    def toggle(raw_element: Any, element: AutomationElement) -> bool:
        """Toggle checkbox or radio button via TogglePattern."""
        ControlPatternManager.validate_element_action(
            raw_element, element, "TogglePattern"
        )
        try:
            if hasattr(raw_element, "toggle"):
                raw_element.toggle()
                return True
            elif hasattr(raw_element, "iface_toggle") and raw_element.iface_toggle:
                raw_element.iface_toggle.Toggle()
                return True
            raise PatternNotSupportedError("Raw element missing toggle implementation.")
        except Exception as exc:
            raise ElementStaleError(
                f"Failed to toggle element '{element.name}'", cause=exc
            )

    @staticmethod
    def select(raw_element: Any, element: AutomationElement) -> bool:
        """Select item via SelectionItemPattern."""
        ControlPatternManager.validate_element_action(
            raw_element, element, "SelectionItemPattern"
        )
        try:
            if hasattr(raw_element, "select"):
                raw_element.select()
                return True
            elif (
                hasattr(raw_element, "iface_selection_item")
                and raw_element.iface_selection_item
            ):
                raw_element.iface_selection_item.Select()
                return True
            raise PatternNotSupportedError("Raw element missing select implementation.")
        except Exception as exc:
            raise ElementStaleError(
                f"Failed to select element '{element.name}'", cause=exc
            )

    @staticmethod
    def expand(raw_element: Any, element: AutomationElement) -> bool:
        """Expand tree/combo element via ExpandCollapsePattern."""
        ControlPatternManager.validate_element_action(
            raw_element, element, "ExpandCollapsePattern"
        )
        try:
            if hasattr(raw_element, "expand"):
                raw_element.expand()
                return True
            elif (
                hasattr(raw_element, "iface_expand_collapse")
                and raw_element.iface_expand_collapse
            ):
                raw_element.iface_expand_collapse.Expand()
                return True
            raise PatternNotSupportedError("Raw element missing expand implementation.")
        except Exception as exc:
            raise ElementStaleError(
                f"Failed to expand element '{element.name}'", cause=exc
            )

    @staticmethod
    def collapse(raw_element: Any, element: AutomationElement) -> bool:
        """Collapse tree/combo element via ExpandCollapsePattern."""
        ControlPatternManager.validate_element_action(
            raw_element, element, "ExpandCollapsePattern"
        )
        try:
            if hasattr(raw_element, "collapse"):
                raw_element.collapse()
                return True
            elif (
                hasattr(raw_element, "iface_expand_collapse")
                and raw_element.iface_expand_collapse
            ):
                raw_element.iface_expand_collapse.Collapse()
                return True
            raise PatternNotSupportedError(
                "Raw element missing collapse implementation."
            )
        except Exception as exc:
            raise ElementStaleError(
                f"Failed to collapse element '{element.name}'", cause=exc
            )
