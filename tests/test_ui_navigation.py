"""Unit tests for NavigationManager."""

from app.ui.navigation.navigation_manager import NavigationManager


def test_navigation_manager_switching():
    nm = NavigationManager()
    assert nm.current_index == 0
    assert nm.current_key == "home"

    nm.navigate_to_index(1)
    assert nm.current_index == 1
    assert nm.current_key == "assistant"

    nm.navigate_to_key("automation")
    assert nm.current_key == "automation"
