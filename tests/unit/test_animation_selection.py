"""Native renderer animation selection tests (Phase 16)."""

import pytest

from events import AnimationController, AppEvent
from pet_sprite import ANIMATIONS


@pytest.mark.unit
class TestNativeAnimationSelection:
    def test_complete_catalog_is_available_to_controller(self):
        controller = AnimationController(ANIMATIONS)
        assert controller.resolve(AppEvent("reminder", "due")) == "Alert"
        assert controller.resolve(AppEvent("windows", "removed")) == "EmptyTrash"

    @pytest.mark.parametrize("name", [
        "RestPose", "Idle1_1", "Explain", "Alert", "IdleSnooze",
        "Save", "Print", "SendMail", "EmptyTrash",
    ])
    def test_required_native_animation_exists(self, name):
        assert name in ANIMATIONS
        assert ANIMATIONS[name]

    def test_unknown_animation_fallback_exists(self):
        assert ANIMATIONS["RestPose"] == [[0, 0, 100]]
