"""Domain models for Phase 6.1 UI Automation Foundation subsystem."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MatchMode(str, Enum):
    """Locator string matching modes."""

    EXACT = "EXACT"
    CASE_INSENSITIVE = "CASE_INSENSITIVE"
    CONTAINS = "CONTAINS"
    STARTS_WITH = "STARTS_WITH"


class ElementSearchStatus(str, Enum):
    """Status codes for semantic element search results."""

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    LIMIT_REACHED = "LIMIT_REACHED"
    ERROR = "ERROR"


class WindowSearchStatus(str, Enum):
    """Status codes for top-level window resolution results."""

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    AMBIGUOUS = "AMBIGUOUS"
    ERROR = "ERROR"


class UIAStatus(str, Enum):
    """Health status for UI Automation subsystem."""

    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


# Standard normalized Windows control types
NORMALIZED_CONTROL_TYPES = {
    "window": "Window",
    "button": "Button",
    "edit": "Edit",
    "text": "Text",
    "checkbox": "CheckBox",
    "radiobutton": "RadioButton",
    "combobox": "ComboBox",
    "list": "List",
    "listitem": "ListItem",
    "menu": "Menu",
    "menuitem": "MenuItem",
    "tab": "Tab",
    "tabitem": "TabItem",
    "tree": "Tree",
    "treeitem": "TreeItem",
    "datagrid": "DataGrid",
    "dataitem": "DataItem",
    "slider": "Slider",
    "progressbar": "ProgressBar",
    "scrollbar": "ScrollBar",
    "toolbar": "ToolBar",
    "statusbar": "StatusBar",
    "image": "Image",
    "hyperlink": "Hyperlink",
    "document": "Document",
    "pane": "Pane",
    "group": "Group",
}


def normalize_control_type(control_type: str | None) -> str:
    """Normalize raw UIA control type string into standard Windows control type."""
    if not control_type:
        return "Pane"
    cleaned = str(control_type).strip()
    if cleaned.lower().startswith("uia_") and cleaned.lower().endswith("controltypeid"):
        cleaned = cleaned[4:-13]
    elif cleaned.lower().endswith("controltype"):
        cleaned = cleaned[:-11]

    key = cleaned.lower()
    return NORMALIZED_CONTROL_TYPES.get(key, cleaned.capitalize() or "Pane")


class BoundingRectangle(BaseModel):
    """Representation of UI element bounding coordinates."""

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0
    width: int = 0
    height: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "left": self.left,
            "top": self.top,
            "right": self.right,
            "bottom": self.bottom,
            "width": self.width,
            "height": self.height,
        }


class AutomationElement(BaseModel):
    """Application-level domain representation of a Windows UI control."""

    element_id: str = Field(
        ..., description="Unique stable identifier for this element instance"
    )
    name: str = Field(default="", description="UI element accessible name")
    automation_id: str = Field(default="", description="UIA AutomationId property")
    control_type: str = Field(
        default="Pane", description="Normalized control type name"
    )
    class_name: str = Field(
        default="", description="Native window class name or UIA ClassName"
    )
    process_id: int = Field(default=0, description="Process ID owning the control")
    window_handle: int = Field(default=0, description="Top-level window HWND handle")
    bounding_rectangle: BoundingRectangle | None = Field(
        default=None, description="Bounding coordinates on screen"
    )
    is_enabled: bool = Field(
        default=True, description="Whether control is interactable/enabled"
    )
    is_visible: bool = Field(default=True, description="Whether element is visible")
    is_offscreen: bool = Field(
        default=False, description="Whether element is scrolled offscreen"
    )
    framework_id: str = Field(
        default="", description="UI Framework identifier (Win32, WPF, Chrome, etc.)"
    )
    native_window_handle: int = Field(
        default=0, description="Native HWND handle for the control if available"
    )
    parent_element_id: str | None = Field(
        default=None, description="Parent element ID if known"
    )
    depth: int = Field(default=0, description="Tree depth relative to root window")
    supported_patterns: list[str] = Field(
        default_factory=list, description="Supported UIA control patterns"
    )
    has_keyboard_focus: bool = Field(
        default=False, description="Whether element currently has focus"
    )
    is_keyboard_focusable: bool = Field(
        default=False, description="Whether element accepts keyboard focus"
    )
    localized_control_type: str = Field(
        default="", description="Localized control type description"
    )
    help_text: str = Field(
        default="", description="Help or tool tip text associated with element"
    )
    value: str | None = Field(
        default=None, description="Safely extracted text or value (redacted if secure)"
    )
    runtime_id: list[int] | str | None = Field(
        default=None, description="Native UIA runtime identifier"
    )
    is_password: bool = Field(
        default=False, description="Whether element is a secure password field"
    )


class AutomationElementSnapshot(BaseModel):
    """Read-only serializable snapshot of a UI element for diagnostics, CLI, and logging."""

    element_id: str
    name: str
    automation_id: str
    control_type: str
    class_name: str
    process_id: int
    window_handle: int
    bounding_rectangle: dict[str, int] | None = None
    is_enabled: bool
    is_visible: bool
    is_offscreen: bool
    framework_id: str
    supported_patterns: list[str]
    has_keyboard_focus: bool
    is_keyboard_focusable: bool
    value: str | None = None
    is_password: bool = False


class AutomationTreeNode(BaseModel):
    """Machine-readable serializable tree representation of UI hierarchy."""

    element: AutomationElementSnapshot
    depth: int
    children: list["AutomationTreeNode"] = Field(default_factory=list)
    truncated: bool = False


class ElementSearchResult(BaseModel):
    """Structured result for semantic element finder operations."""

    status: ElementSearchStatus
    matched_elements: list[AutomationElement] = Field(default_factory=list)
    match_count: int = 0
    query: dict[str, Any] = Field(default_factory=dict)
    truncated: bool = False
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class WindowCandidate(BaseModel):
    """Metadata for a candidate top-level window during resolution."""

    hwnd: int
    title: str
    process_id: int
    process_name: str
    class_name: str
    is_visible: bool
    is_enabled: bool


class WindowSearchResult(BaseModel):
    """Structured result for top-level window resolution operations."""

    status: WindowSearchStatus
    candidates: list[WindowCandidate] = Field(default_factory=list)
    selected_hwnd: int | None = None
    selected_candidate: WindowCandidate | None = None
    diagnostics: dict[str, Any] = Field(default_factory=dict)
