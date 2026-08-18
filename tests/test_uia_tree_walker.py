"""Unit tests for UITreeWalker bounds, cycle protection, and formatting."""

from app.automation.models import AutomationElement
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
        self.automation_id = f"id_{name.lower()}"
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


def test_tree_walker_simple_traversal():
    walker = UITreeWalker(max_depth=5, max_nodes=50)

    btn_save = MockRawElement("Save", "Button", handle=101)
    btn_cancel = MockRawElement("Cancel", "Button", handle=102)
    pane = MockRawElement(
        "MainPane", "Pane", children=[btn_save, btn_cancel], handle=103
    )
    root = MockRawElement("Notepad", "Window", children=[pane], handle=100)

    root_elem = AutomationElement(
        element_id="elem_root",
        name="Notepad",
        control_type="Window",
        window_handle=100,
        native_window_handle=100,
        process_id=1234,
        depth=0,
    )

    tree_node, truncated = walker.traverse_tree(root, root_elem)
    assert truncated is False
    assert tree_node.element.name == "Notepad"
    assert len(tree_node.children) == 1
    pane_node = tree_node.children[0]
    assert pane_node.element.name == "MainPane"
    assert len(pane_node.children) == 2


def test_tree_walker_depth_limit():
    walker = UITreeWalker(max_depth=1, max_nodes=100)

    btn = MockRawElement("Save", "Button", handle=101)
    pane = MockRawElement("MainPane", "Pane", children=[btn], handle=103)
    root = MockRawElement("Notepad", "Window", children=[pane], handle=100)

    root_elem = AutomationElement(
        element_id="elem_root",
        name="Notepad",
        control_type="Window",
        depth=0,
    )

    tree_node, truncated = walker.traverse_tree(root, root_elem)
    assert truncated is True
    assert tree_node.children[0].truncated is True


def test_tree_walker_node_limit():
    walker = UITreeWalker(max_depth=10, max_nodes=2)

    c1 = MockRawElement("C1", "Button", handle=101)
    c2 = MockRawElement("C2", "Button", handle=102)
    c3 = MockRawElement("C3", "Button", handle=103)
    root = MockRawElement("Root", "Window", children=[c1, c2, c3], handle=100)

    root_elem = AutomationElement(
        element_id="elem_root",
        name="Root",
        control_type="Window",
        depth=0,
    )

    tree_node, truncated = walker.traverse_tree(root, root_elem)
    assert truncated is True


def test_tree_walker_dump_tree_string():
    walker = UITreeWalker(max_depth=5, max_nodes=50)

    btn = MockRawElement("Save", "Button", handle=101)
    root = MockRawElement("Notepad", "Window", children=[btn], handle=100)

    root_elem = AutomationElement(
        element_id="elem_root",
        name="Notepad",
        control_type="Window",
        depth=0,
    )

    dump_str = walker.dump_tree_string(root, root_elem)
    assert "Window 'Notepad'" in dump_str
    assert "Button 'Save'" in dump_str
