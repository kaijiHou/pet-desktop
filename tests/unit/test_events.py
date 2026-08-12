"""Phase 15 event-to-animation mapping tests."""

import pytest

from events import AnimationController, AppEvent, EventDispatcher


@pytest.mark.unit
def test_specific_event_animation_mappings():
    available = set(AnimationController.MAPPING.values()) | {"RestPose"}
    controller = AnimationController(available)
    assert controller.resolve(AppEvent("reminder", "due")) == "Alert"
    assert controller.resolve(AppEvent("pocket", "receive")) == "Save"
    assert controller.resolve(AppEvent("file_operation", "copy")) == "Print"
    assert controller.resolve(AppEvent("windows", "removed")) == "EmptyTrash"


@pytest.mark.unit
def test_missing_specific_falls_back_to_category_then_idle():
    assert AnimationController({"GetAttention", "RestPose"}).resolve(
        AppEvent("windows", "added")
    ) == "GetAttention"
    assert AnimationController({"RestPose"}).resolve(AppEvent("unknown", "event")) == "RestPose"
    assert AnimationController(set()).resolve(AppEvent("unknown", "event")) is None


@pytest.mark.unit
def test_dispatcher_delivers_typed_event(qapp):
    dispatcher = EventDispatcher()
    received = []
    dispatcher.event_received.connect(received.append)
    event = AppEvent("pocket", "receive", {"count": 2})
    dispatcher.dispatch(event)
    assert received == [event]
