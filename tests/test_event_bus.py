"""Unit tests for EventBus."""

from app.services.events.event_bus import EventBus
from app.services.events.event_models import ApplicationStarted, Event


def test_event_bus_pub_sub():
    eb = EventBus()
    eb.clear()

    received_events: list[Event] = []

    def handler(event: Event) -> None:
        received_events.append(event)

    eb.subscribe(ApplicationStarted, handler)
    event = ApplicationStarted(app_name="TestApp", version="1.0", environment="test")
    eb.publish(event)

    assert len(received_events) == 1
    assert received_events[0].event_type == "ApplicationStarted"

    eb.unsubscribe(ApplicationStarted, handler)
    eb.publish(event)
    assert len(received_events) == 1


def test_event_bus_wildcard():
    eb = EventBus()
    eb.clear()

    received: list[Event] = []
    eb.subscribe("*", lambda e: received.append(e))

    eb.publish(Event(sender="unit_test"))
    assert len(received) == 1
