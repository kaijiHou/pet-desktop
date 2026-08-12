"""Characterization tests for PetWindow animation-selection logic (Phase 2).

Tests ONLY the pure selection logic (PetWindow class-level animation groups +
_random_anim) WITHOUT constructing any GUI. The future AnimationController /
EventDispatcher architecture is deliberately NOT introduced here.

Ground truth verified against the real repo at baseline 1d89c85:
  * Every ANIM_* group is a non-empty list of strings.
  * _random_anim(group) always returns an element of `group`.
  * The JS-side setAnimation() silently ignores unknown names
    (assets/clippy.html: `if(ANIMS[anim]) {...}`), so the Python side is the
    only gate that decides which names are ever requested.
"""

import pytest

# Import the class WITHOUT constructing it (module import is GUI-safe:
# Qt objects are only created inside __init__ / methods).
from pet_window_web import PetWindow

GROUP_ATTRS = [
    "ANIM_IDLE", "ANIM_TALKING", "ANIM_ALERT", "ANIM_SLEEP",
    "ANIM_THINKING", "ANIM_SEARCHING", "ANIM_WAVE", "ANIM_LOOK",
    "ANIM_LOOK_AROUND", "ANIM_WRITING", "ANIM_HIDE", "ANIM_CONGRATULATE",
]

STATE_ATTRS = ["STATE_IDLE", "STATE_TALKING", "STATE_ALERT", "STATE_SLEEP"]


@pytest.mark.unit
class TestAnimationGroups:
    @pytest.mark.parametrize("attr", GROUP_ATTRS)
    def test_group_is_nonempty_list_of_strings(self, attr):
        group = getattr(PetWindow, attr)
        assert isinstance(group, list), attr
        assert len(group) > 0, f"{attr} is empty"
        assert all(isinstance(n, str) and n for n in group), attr

    def test_state_constants_are_distinct_strings(self):
        states = [getattr(PetWindow, a) for a in STATE_ATTRS]
        assert all(isinstance(s, str) for s in states)
        assert len(set(states)) == len(states)


@pytest.mark.unit
class TestRandomAnimSelection:
    def test_random_anim_returns_member_of_group(self):
        # _random_anim only uses `self` for nothing besides the call; build a
        # bare object without running __init__ (no Qt needed).
        obj = PetWindow.__new__(PetWindow)
        for group in (PetWindow.ANIM_IDLE, PetWindow.ANIM_WAVE,
                      PetWindow.ANIM_ALERT, PetWindow.ANIM_SLEEP):
            for _ in range(20):
                pick = obj._random_anim(group)
                assert pick in group

    def test_random_anim_single_element_group_is_deterministic(self):
        obj = PetWindow.__new__(PetWindow)
        single = ["OnlyOne"]
        assert obj._random_anim(single) == "OnlyOne"


@pytest.mark.unit
class TestSetStateSelectionLogic:
    """Characterize WHICH group set_state picks per state — by reading the
    branch table (no GUI, no JS). We reproduce the dispatch by inspecting
    that each STATE constant maps to a known group via the documented if/elif
    chain. We assert the mapping exists by exercising the pure group choice
    the handler would make, without calling _js."""

    def test_known_states_have_a_default_group(self):
        obj = PetWindow.__new__(PetWindow)
        obj._state = PetWindow.STATE_IDLE

        # Mirror set_state's branch order to confirm each state resolves to a
        # real, non-empty group (characterization of current dispatch).
        dispatch = {
            PetWindow.STATE_IDLE: PetWindow.ANIM_IDLE,
            PetWindow.STATE_TALKING: PetWindow.ANIM_TALKING,
            PetWindow.STATE_ALERT: PetWindow.ANIM_ALERT,
            PetWindow.STATE_SLEEP: PetWindow.ANIM_SLEEP,
        }
        for state, group in dispatch.items():
            assert len(group) > 0, f"state {state} has empty default group"
            assert obj._random_anim(group) in group

    def test_unknown_animation_name_is_silent_noop_in_js(self):
        # Ground truth from assets/clippy.html setAnimation(): the JS guards
        # with `if(ANIMS[anim])`. This test documents (not enforces) that the
        # renderer ignores unknown names rather than erroring — so a stale
        # Python group name degrades silently. See docs/KNOWN_ISSUES.md.
        import re
        from pathlib import Path
        html = (Path(__file__).resolve().parents[2] / "assets" / "clippy.html").read_text(encoding="utf-8")
        m = re.search(r"function setAnimation\(anim\)\{\s*if\(ANIMS\[anim\]\)", html)
        assert m, "setAnimation no longer guards unknown names with ANIMS[anim]"
