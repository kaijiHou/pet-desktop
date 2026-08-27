"""Native renderer animation selection tests (V2).

V2 update: AnimationController uses semantic names. The catalog test now
verifies that semantic names resolve correctly (not Clippy names).
"""

import pytest
from events import AnimationController, AppEvent
from pet_sprite import ANIMATIONS


@pytest.mark.unit
class TestNativeAnimationSelection:
    def test_semantic_mapping_resolves_correctly(self):
        ctrl = AnimationController(set(AnimationController.MAPPING.values()) - {None})
        assert ctrl.resolve(AppEvent("reminder", "due")) == "REMINDER"
        assert ctrl.resolve(AppEvent("windows", "removed")) == "DELETE_FILE"

    @pytest.mark.parametrize("name", [
        "RestPose", "Idle1_1", "Explain", "Alert", "IdleSnooze",
        "Save", "Print", "SendMail", "EmptyTrash",
    ])
    def test_required_sprite_animation_exists(self, name):
        """Legacy sprite sheet still contains all Clippy animations."""
        assert name in ANIMATIONS
        assert ANIMATIONS[name]

    def test_unknown_animation_fallback_exists(self):
        assert ANIMATIONS["RestPose"] == [[0, 0, 100]]
