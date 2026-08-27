"""V2 event-to-animation mapping tests.

V2 update: AnimationController now returns semantic names (REMINDER,
RECEIVE_FILE, DELETE_FILE, ...) instead of legacy Clippy sprite names.
PetWindow translates semantic → concrete name based on character mode.

The controller always falls back to "RestPose" if the name exists in the
available set, so it never returns None when RestPose is available. Test
therefore uses a restricted available set to verify mapping absence.
"""

import pytest

from events import AnimationController, AppEvent, EventDispatcher


@pytest.mark.unit
def test_specific_event_animation_mappings():
    controller = AnimationController(AnimationController.MAPPING.values())
    assert controller.resolve(AppEvent("reminder", "due")) == "REMINDER"
    assert controller.resolve(AppEvent("pocket", "receive")) == "RECEIVE_FILE"
    assert controller.resolve(AppEvent("file_operation", "copy")) == "COPY_FILE"
    assert controller.resolve(AppEvent("windows", "removed")) == "DELETE_FILE"


@pytest.mark.unit
def test_missing_specific_falls_back_to_category():
    ctrl = AnimationController({"COPY_FILE"})
    assert ctrl.resolve(AppEvent("file_operation", "copy")) == "COPY_FILE"
    # windows not in GENERIC → no match → returns None when RestPose absent
    assert ctrl.resolve(AppEvent("windows", "added")) is None


@pytest.mark.unit
def test_restpose_is_always_fallback():
    """When RestPose is in available, controller never returns None."""
    ctrl = AnimationController({"RestPose"})
    assert ctrl.resolve(AppEvent("unknown", "x")) == "RestPose"


@pytest.mark.unit
def test_modified_and_renamed_from_not_mapped_to_specific_animation():
    """Noise-prone events should not produce distinctive animations."""
    ctrl = AnimationController(AnimationController.MAPPING.values())
    assert ctrl.resolve(AppEvent("windows", "modified")) is None
    assert ctrl.resolve(AppEvent("windows", "renamed_from")) is None


@pytest.mark.unit
def test_dispatcher_delivers_typed_event(qapp):
    dispatcher = EventDispatcher()
    received = []
    dispatcher.event_received.connect(received.append)
    event = AppEvent("pocket", "receive", {"count": 2})
    dispatcher.dispatch(event)
    assert received == [event]
