"""Unit tests for ElementFinder semantic search and locator matching modes."""

from app.automation.models import (
    AutomationElement,
    ElementSearchStatus,
    MatchMode,
)
from app.automation.uia.element_finder import ElementFinder
from app.automation.uia.tree_walker import UITreeWalker


class MockRawElement:
    def __init__(
        self,
        name: str,
        control_type: str,
        children: list | None = None,
        handle: int = 100,
    ):
        self.name = name
        self.control_type = control_type
        self.automation_id = (
            f"btn_{name.lower()}" if "save" in name.lower() else f"id_{name.lower()}"
        )
        self.class_name = f"Class_{control_type}"
        self.process_id = 1234
        self.handle = handle
        self.native_window_handle = handle
        self.enabled = True
        self.visible = True
        self.offscreen = False
        self.framework_id = "Win32"
        self._children = children or []

    def children(self):
        return self._children


def test_element_finder_exact_matching():
    walker = UITreeWalker()
    finder = ElementFinder(tree_walker=walker)

    btn_save = MockRawElement("Save", "Button", handle=101)
    btn_cancel = MockRawElement("Cancel", "Button", handle=102)
    root = MockRawElement(
        "Notepad", "Window", children=[btn_save, btn_cancel], handle=100
    )

    root_elem = AutomationElement(
        element_id="elem_root",
        name="Notepad",
        control_type="Window",
        depth=0,
    )

    res = finder.find_by_name(
        "Save", match_mode=MatchMode.EXACT, raw_root=root, root_element=root_elem
    )
    assert res.status == ElementSearchStatus.FOUND
    assert res.match_count == 1
    assert res.matched_elements[0].name == "Save"


def test_element_finder_contains_matching():
    walker = UITreeWalker()
    finder = ElementFinder(tree_walker=walker)

    btn_save = MockRawElement("Save File As...", "Button", handle=101)
    root = MockRawElement("Notepad", "Window", children=[btn_save], handle=100)

    root_elem = AutomationElement(
        element_id="elem_root",
        name="Notepad",
        control_type="Window",
        depth=0,
    )

    res = finder.find_by_name(
        "Save", match_mode=MatchMode.CONTAINS, raw_root=root, root_element=root_elem
    )
    assert res.status == ElementSearchStatus.FOUND
    assert res.match_count == 1
    assert res.matched_elements[0].name == "Save File As..."


def test_element_finder_ambiguity_detection():
    walker = UITreeWalker()
    finder = ElementFinder(tree_walker=walker)

    btn_save1 = MockRawElement("Save", "Button", handle=101)
    btn_save2 = MockRawElement("Save", "Button", handle=102)
    root = MockRawElement(
        "Notepad", "Window", children=[btn_save1, btn_save2], handle=100
    )

    root_elem = AutomationElement(
        element_id="elem_root",
        name="Notepad",
        control_type="Window",
        depth=0,
    )

    res = finder.find_by_name(
        "Save", match_mode=MatchMode.EXACT, raw_root=root, root_element=root_elem
    )
    assert res.status == ElementSearchStatus.AMBIGUOUS
    assert res.match_count == 2


def test_element_finder_combined_criteria():
    walker = UITreeWalker()
    finder = ElementFinder(tree_walker=walker)

    lbl_save = MockRawElement("Save", "Text", handle=101)
    btn_save = MockRawElement("Save", "Button", handle=102)
    root = MockRawElement(
        "Notepad", "Window", children=[lbl_save, btn_save], handle=100
    )

    root_elem = AutomationElement(
        element_id="elem_root",
        name="Notepad",
        control_type="Window",
        depth=0,
    )

    res = finder.find_by_properties(
        {"name": "Save", "control_type": "Button"},
        match_mode=MatchMode.EXACT,
        raw_root=root,
        root_element=root_elem,
    )
    assert res.status == ElementSearchStatus.FOUND
    assert res.match_count == 1
    assert res.matched_elements[0].control_type == "Button"


def test_element_finder_not_found():
    walker = UITreeWalker()
    finder = ElementFinder(tree_walker=walker)

    btn_save = MockRawElement("Save", "Button", handle=101)
    root = MockRawElement("Notepad", "Window", children=[btn_save], handle=100)

    root_elem = AutomationElement(
        element_id="elem_root",
        name="Notepad",
        control_type="Window",
        depth=0,
    )

    res = finder.find_by_name(
        "NonExistent", match_mode=MatchMode.EXACT, raw_root=root, root_element=root_elem
    )
    assert res.status == ElementSearchStatus.NOT_FOUND
    assert res.match_count == 0
