"""Unit tests for tool EventBus signals."""

from app.services.events.event_bus import EventBus
from app.tools.builtin.echo_tool import EchoTool
from app.tools.events.tool_events import ToolRegistered
from app.tools.registry.tool_registry import ToolRegistry


def test_tool_registered_event_publication():
    bus = EventBus()
    bus.clear()

    received_events = []

    def handler(evt):
        received_events.append(evt)

    bus.subscribe(ToolRegistered, handler)

    registry = ToolRegistry(event_bus=bus)
    registry.clear()

    echo = EchoTool()
    registry.register_tool(echo)

    assert len(received_events) == 1
    assert received_events[0].event_type == "ToolRegistered"
    assert received_events[0].tool_id == "system.echo"
