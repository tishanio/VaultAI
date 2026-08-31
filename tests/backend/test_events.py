"""Tests for event system."""
from vault.events import Event


def test_event_creation():
    event = Event(
        event_type="test.event",
        data={"key": "value"},
        source="api-gateway",
    )
    assert event.event_type == "test.event"
    assert event.source == "api-gateway"
    assert event.data == {"key": "value"}


def test_event_creation_with_metadata():
    event = Event(
        event_type="user.created",
        data={"user_id": "123", "trace_id": "abc"},
        source="api-gateway",
    )
    assert event.event_type == "user.created"
    assert event.data["trace_id"] == "abc"


def test_event_to_dict():
    event = Event(
        event_type="subscription.created",
        data={"sub_id": "456"},
        source="market-matching",
    )
    d = event.to_dict()
    assert d["event_type"] == "subscription.created"
    assert d["source"] == "market-matching"
    assert "timestamp" in d
