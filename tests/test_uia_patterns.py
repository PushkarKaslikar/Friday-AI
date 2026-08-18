"""Unit tests for UIA control pattern discovery, safe actions, and security redaction."""

import pytest

from app.automation.errors import (
    ElementInvalidError,
    ElementStaleError,
    PatternNotSupportedError,
)
from app.automation.models import AutomationElement
from app.automation.uia.control_patterns import ControlPatternManager


class MockRawPatternElement:
    def __init__(
        self,
        name: str,
        value: str = "",
        is_password: bool = False,
        enabled: bool = True,
    ):
        self.name = name
        self._value = value
        self.is_password = is_password
        self.enabled = enabled
        self.invoked = False
        self.toggled = False
        self.selected = False
        self.expanded = False
        self.collapsed = False
        self.stale = False

    def invoke(self):
        if self.stale:
            raise RuntimeError("Element destroyed")
        self.invoked = True

    def set_edit_text(self, val: str):
        if self.stale:
            raise RuntimeError("Element destroyed")
        self._value = val

    def window_text(self):
        if self.stale:
            raise RuntimeError("Element destroyed")
        return self._value

    def toggle(self):
        if self.stale:
            raise RuntimeError("Element destroyed")
        self.toggled = not self.toggled

    def select(self):
        if self.stale:
            raise RuntimeError("Element destroyed")
        self.selected = True

    def expand(self):
        if self.stale:
            raise RuntimeError("Element destroyed")
        self.expanded = True

    def collapse(self):
        if self.stale:
            raise RuntimeError("Element destroyed")
        self.collapsed = True


def test_pattern_invoke_action():
    raw = MockRawPatternElement("Submit")
    elem = AutomationElement(
        element_id="e1",
        name="Submit",
        control_type="Button",
        is_enabled=True,
        supported_patterns=["InvokePattern"],
    )

    assert ControlPatternManager.invoke(raw, elem) is True
    assert raw.invoked is True


def test_pattern_value_set_and_get():
    raw = MockRawPatternElement("Username", value="initial")
    elem = AutomationElement(
        element_id="e2",
        name="Username",
        control_type="Edit",
        is_enabled=True,
        supported_patterns=["ValuePattern"],
    )

    assert ControlPatternManager.set_value(raw, elem, "john_doe") is True
    assert ControlPatternManager.get_value(raw, elem) == "john_doe"


def test_pattern_password_redaction():
    raw = MockRawPatternElement("Password", value="secret123", is_password=True)
    elem = AutomationElement(
        element_id="e3",
        name="Password",
        control_type="Edit",
        is_enabled=True,
        is_password=True,
        value="[REDACTED]",
        supported_patterns=["ValuePattern"],
    )

    assert ControlPatternManager.get_value(raw, elem) == "[REDACTED]"


def test_pattern_disabled_element_rejection():
    raw = MockRawPatternElement("Save", enabled=False)
    elem = AutomationElement(
        element_id="e4",
        name="Save",
        control_type="Button",
        is_enabled=False,
        supported_patterns=["InvokePattern"],
    )

    with pytest.raises(ElementInvalidError):
        ControlPatternManager.invoke(raw, elem)


def test_pattern_unsupported_pattern_rejection():
    raw = MockRawPatternElement("Save")
    elem = AutomationElement(
        element_id="e5",
        name="Save",
        control_type="Button",
        is_enabled=True,
        supported_patterns=["InvokePattern"],
    )

    with pytest.raises(PatternNotSupportedError):
        ControlPatternManager.toggle(raw, elem)


def test_pattern_stale_element_error():
    raw = MockRawPatternElement("Save")
    raw.stale = True
    elem = AutomationElement(
        element_id="e6",
        name="Save",
        control_type="Button",
        is_enabled=True,
        supported_patterns=["InvokePattern"],
    )

    with pytest.raises(ElementStaleError):
        ControlPatternManager.invoke(raw, elem)


def test_pattern_toggle_select_expand_collapse():
    raw = MockRawPatternElement("Options")
    elem = AutomationElement(
        element_id="e7",
        name="Options",
        control_type="CheckBox",
        is_enabled=True,
        supported_patterns=[
            "TogglePattern",
            "SelectionItemPattern",
            "ExpandCollapsePattern",
        ],
    )

    assert ControlPatternManager.toggle(raw, elem) is True
    assert raw.toggled is True

    assert ControlPatternManager.select(raw, elem) is True
    assert raw.selected is True

    assert ControlPatternManager.expand(raw, elem) is True
    assert raw.expanded is True

    assert ControlPatternManager.collapse(raw, elem) is True
    assert raw.collapsed is True
