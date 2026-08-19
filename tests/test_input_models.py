"""Unit tests for Phase 6.2 input subsystem domain models and target resolution."""

import pytest

from app.automation.input.errors import InvalidCoordinatesError, InvalidTargetError
from app.automation.input.models import (
    EasingProfile,
    InputTarget,
    MouseButton,
    TargetType,
    TypingProfile,
    get_typing_interval_seconds,
)
from app.automation.input.target_resolver import TargetResolver
from app.automation.models import AutomationElement, BoundingRectangle


def test_input_models_enums() -> None:
    """Verify enum values and helper functions."""
    assert MouseButton.LEFT.value == "LEFT"
    assert MouseButton.RIGHT.value == "RIGHT"
    assert MouseButton.MIDDLE.value == "MIDDLE"

    assert EasingProfile.LINEAR.value == "LINEAR"
    assert EasingProfile.EASE_IN_OUT.value == "EASE_IN_OUT"
    assert EasingProfile.SMOOTH.value == "SMOOTH"

    assert TypingProfile.INSTANT.value == "INSTANT"
    assert get_typing_interval_seconds(TypingProfile.INSTANT) == 0.0
    assert get_typing_interval_seconds(TypingProfile.FAST) == 0.02
    assert get_typing_interval_seconds(TypingProfile.NORMAL) == 0.05
    assert get_typing_interval_seconds(TypingProfile.SLOW) == 0.12


def test_target_resolver_screen_coordinate() -> None:
    """Verify resolving valid screen coordinates."""
    resolver = TargetResolver(bounds_check_enabled=False)
    target = InputTarget(target_type=TargetType.SCREEN_COORDINATE, x=400, y=300)
    pos = resolver.resolve_target(target)
    assert pos.x == 400
    assert pos.y == 300


def test_target_resolver_uia_element() -> None:
    """Verify converting AutomationElement bounding rectangle center to position."""
    resolver = TargetResolver(bounds_check_enabled=False)
    elem = AutomationElement(
        element_id="btn_1",
        name="Submit",
        control_type="Button",
        is_enabled=True,
        bounding_rectangle=BoundingRectangle(
            left=100, top=100, right=200, bottom=200, width=100, height=100
        ),
    )
    target = InputTarget(target_type=TargetType.UIA_ELEMENT, element=elem)
    pos = resolver.resolve_target(target)
    assert pos.x == 150
    assert pos.y == 150


def test_target_resolver_disabled_element_fails() -> None:
    """Verify disabled UIA target raises InvalidTargetError."""
    resolver = TargetResolver(bounds_check_enabled=False)
    elem = AutomationElement(
        element_id="btn_2",
        name="Cancel",
        control_type="Button",
        is_enabled=False,
        bounding_rectangle=BoundingRectangle(
            left=0, top=0, right=50, bottom=50, width=50, height=50
        ),
    )
    target = InputTarget(target_type=TargetType.UIA_ELEMENT, element=elem)
    with pytest.raises(InvalidTargetError, match="disabled"):
        resolver.resolve_target(target)


def test_target_resolver_invalid_coordinates() -> None:
    """Verify bounds check raises InvalidCoordinatesError for out-of-bounds targets."""
    resolver = TargetResolver(bounds_check_enabled=True)
    target = InputTarget(target_type=TargetType.SCREEN_COORDINATE, x=-99999, y=-99999)
    with pytest.raises(InvalidCoordinatesError):
        resolver.resolve_target(target)
