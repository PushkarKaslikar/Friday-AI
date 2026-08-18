"""Adapter converting pywinauto element info objects to domain AutomationElement models."""

import uuid
from typing import Any

from app.automation.errors import ElementStaleError
from app.automation.models import (
    AutomationElement,
    AutomationElementSnapshot,
    BoundingRectangle,
    normalize_control_type,
)
from app.logging import logger


class ElementAdapter:
    """Safely extracts properties and creates domain models from underlying pywinauto elements."""

    @staticmethod
    def create_automation_element(
        raw_element: Any,
        parent_id: str | None = None,
        depth: int = 0,
        assigned_id: str | None = None,
    ) -> AutomationElement:
        """Construct an AutomationElement domain object from a pywinauto element or info wrapper."""
        if raw_element is None:
            raise ElementStaleError("Cannot adapt None element reference.")

        element_id = assigned_id or f"elem_{uuid.uuid4().hex[:12]}"

        # Access element_info if available (pywinauto standard wrapper)
        info = getattr(raw_element, "element_info", raw_element)

        try:
            name = str(getattr(info, "name", "") or "")
            automation_id = str(getattr(info, "automation_id", "") or "")
            raw_ctrl_type = str(getattr(info, "control_type", "") or "Pane")
            control_type = normalize_control_type(raw_ctrl_type)
            class_name = str(getattr(info, "class_name", "") or "")
            process_id = int(getattr(info, "process_id", 0) or 0)
            handle = int(getattr(info, "handle", 0) or 0)

            # Bounding rectangle extraction
            rect_obj = getattr(info, "rectangle", None)
            bounding_rect: BoundingRectangle | None = None
            if rect_obj is not None:
                try:
                    left = int(getattr(rect_obj, "left", 0))
                    top = int(getattr(rect_obj, "top", 0))
                    right = int(getattr(rect_obj, "right", 0))
                    bottom = int(getattr(rect_obj, "bottom", 0))
                    width = max(0, right - left)
                    height = max(0, bottom - top)
                    bounding_rect = BoundingRectangle(
                        left=left,
                        top=top,
                        right=right,
                        bottom=bottom,
                        width=width,
                        height=height,
                    )
                except Exception:
                    bounding_rect = None

            is_enabled = bool(getattr(info, "enabled", True))
            is_visible = bool(getattr(info, "visible", True))
            is_offscreen = bool(getattr(info, "offscreen", False))
            framework_id = str(getattr(info, "framework_id", "") or "")
            native_hwnd = int(getattr(info, "native_window_handle", handle) or handle)

            # Focus & localization
            has_focus = bool(getattr(info, "has_keyboard_focus", False))
            is_focusable = bool(getattr(info, "is_keyboard_focusable", False))
            loc_ctrl_type = str(getattr(info, "localized_control_type", "") or "")
            help_text = str(getattr(info, "help_text", "") or "")

            # Runtime ID
            runtime_id_raw = getattr(info, "runtime_id", None)
            runtime_id = (
                list(runtime_id_raw)
                if isinstance(runtime_id_raw, (list, tuple))
                else None
            )

            # Pattern discovery
            supported_patterns = ElementAdapter.extract_supported_patterns(raw_element)

            # Secure field detection & value extraction
            is_password = ElementAdapter.is_secure_field(raw_element, info)
            value: str | None = None

            if is_password:
                value = "[REDACTED]"
            else:
                value = ElementAdapter.extract_safe_value(raw_element)

            return AutomationElement(
                element_id=element_id,
                name=name,
                automation_id=automation_id,
                control_type=control_type,
                class_name=class_name,
                process_id=process_id,
                window_handle=handle,
                bounding_rectangle=bounding_rect,
                is_enabled=is_enabled,
                is_visible=is_visible,
                is_offscreen=is_offscreen,
                framework_id=framework_id,
                native_window_handle=native_hwnd,
                parent_element_id=parent_id,
                depth=depth,
                supported_patterns=supported_patterns,
                has_keyboard_focus=has_focus,
                is_keyboard_focusable=is_focusable,
                localized_control_type=loc_ctrl_type,
                help_text=help_text,
                value=value,
                runtime_id=runtime_id,
                is_password=is_password,
            )
        except Exception as exc:
            logger.debug(f"Failed to adapt raw element: {exc}")
            raise ElementStaleError(
                "Failed to extract properties from element reference", cause=exc
            )

    @staticmethod
    def create_snapshot(element: AutomationElement) -> AutomationElementSnapshot:
        """Convert domain AutomationElement to read-only snapshot model."""
        return AutomationElementSnapshot(
            element_id=element.element_id,
            name=element.name,
            automation_id=element.automation_id,
            control_type=element.control_type,
            class_name=element.class_name,
            process_id=element.process_id,
            window_handle=element.window_handle,
            bounding_rectangle=element.bounding_rectangle.to_dict()
            if element.bounding_rectangle
            else None,
            is_enabled=element.is_enabled,
            is_visible=element.is_visible,
            is_offscreen=element.is_offscreen,
            framework_id=element.framework_id,
            supported_patterns=element.supported_patterns,
            has_keyboard_focus=element.has_keyboard_focus,
            is_keyboard_focusable=element.is_keyboard_focusable,
            value=element.value,
            is_password=element.is_password,
        )

    @staticmethod
    def extract_supported_patterns(raw_element: Any) -> list[str]:
        """Discover supported UIA pattern names for an element safely."""
        patterns: list[str] = []
        if hasattr(raw_element, "get_supported_patterns"):
            try:
                raw_patterns = raw_element.get_supported_patterns()
                for p in raw_patterns:
                    name = getattr(p, "__name__", str(p))
                    if name.endswith("Pattern"):
                        patterns.append(name)
                    else:
                        patterns.append(f"{name}Pattern")
                return patterns
            except Exception:
                pass

        # Check standard pattern attributes safely without triggering pywinauto property getter errors
        pattern_checkers = [
            (
                "InvokePattern",
                lambda e: bool(
                    getattr(e, "invoke", None) or getattr(e, "iface_invoke", None)
                ),
            ),
            (
                "ValuePattern",
                lambda e: bool(
                    getattr(e, "set_edit_text", None) or getattr(e, "iface_value", None)
                ),
            ),
            (
                "TogglePattern",
                lambda e: bool(
                    getattr(e, "toggle", None) or getattr(e, "iface_toggle", None)
                ),
            ),
            (
                "SelectionPattern",
                lambda e: bool(getattr(e, "iface_selection", None)),
            ),
            (
                "SelectionItemPattern",
                lambda e: bool(
                    getattr(e, "select", None)
                    or getattr(e, "iface_selection_item", None)
                ),
            ),
            (
                "ExpandCollapsePattern",
                lambda e: bool(
                    getattr(e, "expand", None)
                    or getattr(e, "iface_expand_collapse", None)
                ),
            ),
            (
                "ScrollPattern",
                lambda e: bool(
                    getattr(e, "scroll", None) or getattr(e, "iface_scroll", None)
                ),
            ),
            (
                "RangeValuePattern",
                lambda e: bool(getattr(e, "iface_range_value", None)),
            ),
            ("TextPattern", lambda e: bool(getattr(e, "iface_text", None))),
            ("WindowPattern", lambda e: bool(getattr(e, "iface_window", None))),
        ]

        for pattern_name, checker in pattern_checkers:
            try:
                if checker(raw_element):
                    patterns.append(pattern_name)
            except Exception:
                continue

        return patterns

    @staticmethod
    def is_secure_field(raw_element: Any, info: Any) -> bool:
        """Determine if an element is a secure/password field."""
        if bool(getattr(info, "is_password", False)):
            return True

        class_name = str(getattr(info, "class_name", "") or "").lower()
        automation_id = str(getattr(info, "automation_id", "") or "").lower()

        return "password" in class_name or "password" in automation_id

    @staticmethod
    def extract_safe_value(raw_element: Any) -> str | None:
        """Safely extract readable text or value from control."""
        try:
            iface_val = getattr(raw_element, "iface_value", None)
            if iface_val and hasattr(iface_val, "CurrentValue"):
                return str(iface_val.CurrentValue)
        except Exception:
            pass

        try:
            if hasattr(raw_element, "window_text"):
                text = raw_element.window_text()
                if text:
                    return str(text)
        except Exception:
            pass

        return None
